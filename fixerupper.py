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

        game_model = self.get_game_model( 'mega-man-2' )        
        gameinfolist = json.loads( game_model.info )
        for i, gameinfo in enumerate( gameinfolist ):
            if gameinfo['category'] == 'Any%, No Zips':
                del gameinfolist[ i ]
                break

        game_model.info = json.dumps( gameinfolist )
        game_model.put( )
        
        self.write( "FixerUpper complete!\n" )
