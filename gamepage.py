import handler
import runs

from google.appengine.ext import db

class GamePage( handler.Handler ):
    def get( self, game_code ):
        user = self.get_user( )

        # Set this page to be the return page after a login/logout/signup
        self.set_return_url( '/game/' + game_code )

        # Make sure this game exists
        game = self.get_game( game_code )
        if not game:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        rundict = self.get_rundict( game_code )
        
        self.render( "gamepage.html", user=user, game=game, 
                     game_code=game_code, rundict=rundict )
