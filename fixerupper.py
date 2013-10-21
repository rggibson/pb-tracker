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

        # Grab the gamelist
        j = urllib2.urlopen( 
#            'http://www.pbtracker.net/static/json/import_games.json' ).read( )
            'http://localhost:8080/static/json/import_games.json' ).read( )
        gamelist = json.loads( j )

        # Add the games, overwriting any existing versions in database
        self.write( "Adding games to database...\n" )
        for g in gamelist:
            game_code = util.get_code( g['game'] )
            gameinfolist = [ ]
            for category in g['categories']:
                gameinfolist.append( dict( category=category,
                                           bk_runner=None,
                                           bk_seconds=None,
                                           bk_video=None,
                                           bk_updater=None ) )
            game_model = games.Games( game=g['game'],
                                      info=json.dumps( gameinfolist ),
                                      key_name=game_code,
                                      parent=games.key() )
            game_model.put( )
            self.update_cache_game_model( game_code, game_model )
        self.update_cache_all_games( None )
        
        self.write( "FixerUpper complete!\n" )
