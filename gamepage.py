# gamepage.py
# Author: Richard Gibson
#
# Renders individual game pages at /game/<game_code>, where game_code is the 
# game converted through util.get_code().  For each category of the game run, 
# a table lists the PBs for each runner, sorted by time.  The tables 
# themselves are sorted by number of PBs.  These tables are filled through 
# handler.get_gamepage() that returns a list of dictionaries, one for each 
# category run.  Similar to runnerpage.py, for each dictionary d, 
# d['infolist'] is itself a list of dictionaries, one for each runner.
#

import handler
import runs
import util
import logging
import json

from operator import itemgetter

from google.appengine.ext import db
from google.appengine.runtime import DeadlineExceededError

class GamePage( handler.Handler ):
    def get( self, game_code ):
        try:
            user = self.get_user( )
            if user == self.OVER_QUOTA_ERROR:
                user = None

            # Have to take the code of the game code because of percent
            # encoded plusses
            game_code = util.get_code( game_code )

            # Make sure this game exists
            game_model = self.get_game_model( game_code )
            if not game_model:
                self.error( 404 )
                self.render( "404.html", user=user )
                return
            if game_model == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
                return        

            # Find out if this user has run this game
            if user is not None:
                user_has_run = self.get_user_has_run( user.username, 
                                                      game_model.game )
                if user_has_run == self.OVER_QUOTA_ERROR:
                    user_has_run = False
            else:
                user_has_run = False

            # Look for a specific category to display
            category_code = self.request.get( 'c' )
            if category_code:
                category_code = util.get_code( category_code )
            else:
                category_code = None

            # Grab the categories with their codes
            categories = [ ]
            category = None
            for this_category in game_model.categories( ):
                this_category_code = util.get_code( this_category )
                categories.append( dict( category=this_category,
                                         category_code=this_category_code ) )
                if category_code == this_category_code:
                    category = this_category
            categories.sort( key=itemgetter( 'category_code' ) )

            # Grab the page num
            page_num = self.request.get( 'page' )
            try:
                page_num = int( page_num )
            except ValueError:
                page_num = 1
            
            gamepage = self.get_gamepage( game_model.game, category, page_num )
            if gamepage == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
                return
            page_num = gamepage['page_num']
        
            # Add gravatar images to the gamepage
            d = gamepage['d']
            if d is not None:
                for run in d['infolist']:
                    runner = self.get_runner( util.get_code(
                        run['username'] ) )
                    if runner == self.OVER_QUOTA_ERROR:
                        self.error( 403 )
                        if self.format == 'html':
                            self.render( "403.html", user=user )
                        return
                    if runner is not None:
                        run['gravatar_url'] = util.get_gravatar_url( 
                            runner.gravatar, size=20 )
                if len( d['infolist'] ) <= 0 and page_num == 1:
                    # Delete this category for the game model
                    gameinfolist = json.loads( game_model.info )
                    for i, gameinfo in enumerate( gameinfolist ):
                        if category == gameinfo['category']:
                            del gameinfolist[ i ]
                            logging.info( 'Removed ' + category
                                          + ' from ' + game_model.game )
                            if len( gameinfolist ) == 0:
                                # Remove the game
                                game = game_model.game
                                game_model.delete( )
                                logging.info( game + " deleted" )
                                self.update_cache_game_model( game_code, None )
                                # From gamelist in memcache too
                                cached_gamelists = self.get_cached_gamelists( )
                                if cached_gamelists is not None:
                                    done = False
                                    for page_num, res in cached_gamelists.iteritems( ):
                                        if done:
                                            break
                                        for i, d in enumerate( res['gamelist'] ):
                                            if d['game'] == game:
                                                del cached_gamelists[ page_num ]['gamelist'][ i ]
                                                done = True
                                                break
                                    self.update_cache_gamelist(
                                        cached_gamelists )
                                self.error( 404 )
                                self.render( "404.html", user=user )
                                return
                                                
                            else:
                                # Update game
                                game_model.info = json.dumps( gameinfolist )
                                game_model.put( )
                                self.update_cache_game_model( game_code,
                                                              game_model )
                            break
            
            has_prev = False
            if page_num > 1:
                has_prev = True
            
            if self.format == 'html':
                self.render( "gamepage.html", user=user, game=game_model.game, 
                             game_code=game_code, d=d, categories=categories,
                             user_has_run=user_has_run, has_prev=has_prev,
                             has_next=gamepage['has_next'], page_num=page_num )
            elif self.format == 'json':
                if d is None:
                    self.render_json( categories )
                else:
                    self.render_json( d )

        except DeadlineExceededError, msg:
            logging.error( msg )
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )
