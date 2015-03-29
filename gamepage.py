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

from google.appengine.ext import db

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
            
            gamepage = self.get_gamepage( game_model.game )
            if gamepage == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
                return        
        
            # Add gravatar images to the gamepage
            for d in gamepage:
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

            if self.format == 'html':
                self.render( "gamepage.html", user=user, game=game_model.game, 
                             game_code=game_code, gamepage=gamepage,
                             user_has_run=user_has_run )
            elif self.format == 'json':
                self.render_json( gamepage )

        except google.appengine.runtime.DeadlineExceededError:
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )
