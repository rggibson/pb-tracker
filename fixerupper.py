import games
import util
import handler
import urllib2
import json

class FixerUpper( handler.Handler ):
    def get( self ):
        # Make sure it's me
        user = self.get_user( )
        if not user or user.username != "rggibson":
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        self.write( "FixerUpper in progress...\n" )

        old_game_code = 'musya-the-classic-japanese-tail-of-horror'
        new_game_code = 'musya-the-classic-japanese-tale-of-horror'

        game_model = self.get_game_model( old_game_code )        
        game = game_model.game
        info = game_model.info
        game_model.delete( )
        self.update_cache_game_model( old_game_code, None )

        game_model = games.Games( game = game,
                                  info = info,
                                  parent = games.key(),
                                  key_name = new_game_code )
        game_model.put( )
        self.update_cache_game_model( new_game_code, game_model )
        
        self.write( "FixerUpper complete!\n" )
