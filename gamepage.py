import handler
import runs
import util

from google.appengine.ext import db

class GamePage( handler.Handler ):
    def get( self, game_code ):
        user = self.get_user( )

        # Set this page to be the return page after a login/logout/signup
        self.set_return_url( '/game/' + game_code )

        # Make sure this game exists
        game_model = self.get_game_model( game_code )
        if not game_model:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        # Find out if this user has run this game
        if user is not None:
            user_has_run = self.get_user_has_run( user.username, 
                                                  game_model.game )
        else:
            user_has_run = False
            
        gamepage = self.get_gamepage( game_model.game )
        
        # Add gravatar images to the gamepage
        for d in gamepage:
            for run in d['infolist']:
                runner = self.get_runner( util.get_code( run['username'] ) )
                if runner is not None:
                    run['gravatar_url'] = util.get_gravatar_url( 
                        runner.gravatar, size=20 )

        self.render( "gamepage.html", user=user, game=game_model.game, 
                     game_code=game_code, gamepage=gamepage,
                     user_has_run=user_has_run )
