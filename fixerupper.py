# fixerupper.py
# Author: Richard Gibson
#
# An admin-only handler for managing one-time clean-up tasks.  Currently, this
# is the best way to clean up some of the extra games and categories that have
# been submitted that (hopefully unintentionally) have duplicated other
# games.Games entries.  I should probably come up with a better way to 
# manage this, but this class will do the job for now.  I've also used this 
# to fix some of the database entries after a bug was discovered (like bad
# dates on runs). 
# 

import games
import runs
import util
import handler
import json
import logging

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.runtime import apiproxy_errors
from google.appengine.ext.db import BadRequestError

class FixerUpper( handler.Handler ):
    def get( self ):
        QUERY_LIMIT = 1000
        cursor_key = 'fixerupper-cursor'
        
        # Make sure it's me
        user = self.get_user( )
        if not user:
            self.error( 404 )
            self.render( "404.html", user=user )
            return
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return
        elif user.username != "rggibson":
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        c = self.request.get( 'c', default_value=None )

        try:
            # Add missing games and categories back in + update num_pbs
            q = db.Query( runs.Runs, projection=[ 'game', 'category',
                                                  'username' ],
                          distinct=True )
            q.ancestor( runs.key( ) )
            q.order( 'game' )
            if c is None:
                c = memcache.get( cursor_key )
            if c:
                try:
                    q.with_cursor( start_cursor=c )
                    logging.info( "Fixer upper using cursor " + c )
                except BadRequestErro:
                    logging.error( "FixerUpper failed to use cursor" )
                    pass
            game_model = None
            categories = None
            infolist = None
            old_num_pbs = None
            do_update = None
            cursor_to_save = c
            prev_cursor = c
            num_runs = 0
            for run in q.run( limit=QUERY_LIMIT ):
                if game_model is None or game_model.game != run.game:
                    # New game
                    if game_model is not None:
                        # Save previous game model
                        game_model.info = json.dumps( infolist )
                        if do_update or game_model.num_pbs != old_num_pbs:
                            game_model.put( )
                            self.update_cache_game_model( game_code,
                                                          game_model )
                        cursor_to_save = prev_cursor

                    game_code = util.get_code( run.game )
                    game_model = self.get_game_model( game_code )
                    if game_model is None:
                        # Make a new game model
                        game_model = games.Games( game=run.game,
                                                  info=json.dumps( [ ] ),
                                                  num_pbs=0,
                                                  parent=games.key(),
                                                  key_name=game_code )      
                        logging.info( "Fixerupper put new game " + run.game
                                      + " in datastore." )
                    categories = game_model.categories( )
                    infolist = json.loads( game_model.info )
                    old_num_pbs = game_model.num_pbs
                    do_update = False
                    game_model.num_pbs = 0

                game_model.num_pbs += 1
                if run.category not in categories:
                    # Add category
                    infolist.append( dict( category=run.category,
                                           bk_runner=None,
                                           bk_seconds=None, bk_datestr=None,
                                           bk_video=None, bk_updater=None ) )
                    logging.info( "Fixerupper added category " + run.category
                                  + " to " + run.game )
                    categories.append( run.category )
                    do_update = True
                prev_cursor = q.cursor( )
                num_runs += 1
            if game_model is not None and num_runs < QUERY_LIMIT:
                # Save last game model
                game_model.info = json.dumps( infolist )
                game_model.put( )
                self.update_cache_game_model( game_code, game_model )
                cursor_to_save = prev_cursor

            if cursor_to_save == memcache.get( cursor_key ):
                logging.error( "No games updated by FixerUpper." )
                if game_model is not None:
                    logging.error( "Last game was " + game_model.game )
                self.write( "FixerUpper failed to update any games<br>" )
                return

            if memcache.set( cursor_key, cursor_to_save ):
                self.write( "FixerUpper finished and saved cursor "
                            + cursor_to_save )
            else:
                self.write( "FixerUpper finished but failed to save cursor "
                            + cursor_to_save )

        except apiproxy_errors.OverQuotaError, msg:
            logging.error( msg )
            self.write( "FixerUpper failed with over quota error<br>" )
            return

        self.update_cache_categories( None )
