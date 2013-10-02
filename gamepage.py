import handler
import runs

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

        ( gamepage, fresh ) = self.get_gamepage( game_model.game )

        self.render( "gamepage.html", user=user, game=game_model.game, 
                     game_code=game_code, gamepage=gamepage )
