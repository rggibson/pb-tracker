# change_categories.py
# Author: Richard Gibson
#
# A mod-only form for quickly changing all runs of a game, category to a new
# game, category.
#

import runhandler
import util
import logging
import runs
import json
import games

from operator import itemgetter
from google.appengine.ext import db
from google.appengine.api import memcache

class ChangeCategories( runhandler.RunHandler ):
    def get( self ):
        # Get the user
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        # Make sure user is a mod
        if not user.is_mod:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        params = dict( user=user,
                       categories=self.get_categories( ) )

        self.render( "change_categories.html", **params )

    def post( self ):
        # Get the user
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        # Make sure user is a mod
        if not user.is_mod:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        old_game = self.request.get( 'old-game' )
        old_category = self.request.get( 'old-category' )
        new_game = self.request.get( 'new-game' )
        new_category = self.request.get( 'new-category' )

        params = dict( user=user, old_game=old_game, old_category=old_category,
                       new_game=new_game, new_category=new_category )

        valid = True

        # Make sure the new game doesn't already exist under a similar name
        new_game_code = util.get_code( new_game )
        new_game_model = self.get_game_model( new_game_code )
        if not new_game_code:
            params['new_game_error'] = "New game cannot be blank"
            valid = False
        elif new_game_model is not None and new_game != new_game_model.game:
            params['new_game_error'] = ( "New game already exists under [" 
                                         + new_game_model.game 
                                         + "] (case sensitive)."
                                         + " Hit submit again to confirm." )
            params['new_game'] = new_game_model.game
            valid = False
        elif not games.valid_game_or_category( new_game ):
            params['new_game_error'] = ( "Game name must not use any 'funny'"
                                         + " characters and can be up to 100 "
                                         + "characters long" )
            valid = False
        params[ 'new_game_code' ] = new_game_code
        params[ 'new_game_model' ] = new_game_model

        # Make sure the category doesn't already exist under a similar name
        new_category_code = util.get_code( new_category )
        new_category_found = False
        if not new_category_code:
            params['new_category_error'] = "Category cannot be blank"
            valid = False
        elif new_game_model is not None:
            infolist = json.loads( new_game_model.info )
            for info in infolist:
                if new_category_code == util.get_code( info['category'] ):
                    new_category_found = True
                    if new_category != info['category']:
                        params['new_category_error'] = ( "Category already exists "
                                                     + "under [" 
                                                     + info['category'] + "] "
                                                     + "(case sensitive). "
                                                     + "Hit submit again to "
                                                     + "confirm." )
                        params['new_category'] = info['category']
                        valid = False
                    break
        if( not new_category_found 
            and not games.valid_game_or_category( new_category ) ):
            params['new_category_error'] = ( "Category must not use any 'funny'"
                                         + " characters and can be up to 100 "
                                         + "characters long" )
            valid = False
        params[ 'new_category_found' ] = new_category_found

        if not valid:
            self.render( "change_categories.html", **params )
            return

        changes = self.change_categories( params )

        # Render changes
        self.write( changes )
        
    @db.transactional( xg=True )
    def change_categories( self, params ):
        res = ''

        # Grab the old game model
        old_game_code = util.get_code( params['old_game'] )
        if old_game_code == params['new_game_code']:
            old_game_model = params['new_game_model']
        else:
            old_game_model = self.get_game_model( old_game_code )
        if old_game_model is None:
            return "Did not find game [" + params['old_game'] + "]"

        if params['new_game_model'] is None:
            # New game does not exist, so create it
            params['new_game_model'] = games.Games( 
                game = params['new_game'],
                info = json.dumps( [ ] ),
                num_pbs = 0,
                parent = games.key( ),
                key_name = params['new_game_code'] )
            res += ( 'Created new game model for game [' + params['new_game'] 
                     + ']<br>' )
        
        if not params['new_category_found']:
            # Add the new category to the new game model
            gameinfolist = json.loads( params['new_game_model'].info )
            d = dict( category=params['new_category'], 
                      bk_runner=None,
                      bk_seconds=None,
                      bk_video=None,
                      bk_datestr=None,
                      bk_updater=None )
            gameinfolist.append( d )
            params['new_game_model'].info = json.dumps( gameinfolist )
            res += 'Added new category [' + params['new_category'] + ']<br>'

        # Grab the gameinfo for the old game
        oldgameinfolist = json.loads( old_game_model.info )
        oldgameinfo = None
        for g in oldgameinfolist:
            if( util.get_code( params['old_category'] ) == util.get_code( 
                    g['category'] ) ):
                oldgameinfo = g
                break
        if oldgameinfo is None:
            return "Did not find old category [" + params['old_category'] + ']'

        # Grab the gameinfo for the new game
        newgameinfolist = json.loads( params['new_game_model'].info )
        newgameinfo = None
        for g in newgameinfolist:
            if( util.get_code( params['new_category'] ) == util.get_code( 
                    g['category'] ) ):
                newgameinfo = g
                break
        if newgameinfo is None:
            return "Did not find new category [" + params['new_category'] + ']'

        # Update best known time if necessary
        if( oldgameinfo.get( 'bk_seconds' ) is not None
            and ( newgameinfo.get( 'bk_seconds' ) is None 
                  or oldgameinfo.get( 'bk_seconds' ) 
                  < newgameinfo.get( 'bk_seconds' ) ) ):
            newgameinfo['bk_seconds'] = oldgameinfo.get( 'bk_seconds' )
            newgameinfo['bk_runner'] = oldgameinfo.get( 'bk_runner' )
            newgameinfo['bk_datestr'] = oldgameinfo.get( 'bk_datestr' )
            newgameinfo['bk_video'] = oldgameinfo.get( 'bk_video' )
            newgameinfo['bk_updater'] = oldgameinfo.get( 'bk_updater' )
            params['new_game_model'].info = json.dumps( newgameinfolist )
            res += 'Updated bkt<br>'

        # Update num_pbs for old game, new game
        res += ( 'Previous num_pbs for old game, category = ' 
                 + str( old_game_model.num_pbs ) + '<br>' )
        res += ( 'Previous num_pbs for new game, category = ' 
                 + str( params['new_game_model'].num_pbs ) + '<br>' )
        q = db.Query( runs.Runs, projection=['username'], distinct=True )
        q.ancestor( runs.key() )
        q.filter( 'game =', params['old_game'] )
        q.filter( 'category =', params['old_category'] )
        for run in q.run( limit=1000 ):
            old_game_model.num_pbs -= 1
            q2 = db.Query( runs.Runs )
            q2.ancestor( runs.key() )
            q2.filter( 'game =', params['new_game'] )
            q2.filter( 'category =', params['new_category'] )
            q2.filter( 'username =', run.username )
            num_runs = q2.count( limit=1 )
            if num_runs <= 0:
                params['new_game_model'].num_pbs += 1
            else:
                # Need to decrement runner's num_pbs
                runner = self.get_runner( util.get_code( run.username ) )
                runner.num_pbs -= 1
                runner.put( )
                res += ( "Updated " + run.username + " num_pbs from "
                         + str( runner.num_pbs + 1 ) + " to " 
                         + str( runner.num_pbs ) + "<br>" )
                
        res += ( 'Updated num_pbs for old game, category = ' 
                 + str( old_game_model.num_pbs ) + '<br>' )
        res += ( 'Updated num_pbs for new game, category = ' 
                 + str( params['new_game_model'].num_pbs ) + '<br>' )

        # Update old, new game models in database
        old_game_model.put( )
        if old_game_code != params['new_game_code']:
            params['new_game_model'].put( )

        # Change the runs
        res += "<br>Changed runs:<br>"
        q = db.Query( runs.Runs )
        q.ancestor( runs.key() )
        q.filter( 'game =', params['old_game'] )
        q.filter( 'category =', params['old_category'] )
        for run in q.run( limit = 10000 ):
            # Update the run
            run.game = params['new_game']
            run.category = params['new_category']
            run.put( )
            res += ( 'Runner=' + run.username + ' time=' 
                     + util.seconds_to_timestr( run.seconds ) + '<br>' )

        if not memcache.flush_all( ):
            res += "Failed to flush memcache<br>"

        # All dun
        return res
