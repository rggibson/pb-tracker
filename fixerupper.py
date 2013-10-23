import games
import runs
import util
import handler
import urllib2
import json

from google.appengine.ext import db

class FixerUpper( handler.Handler ):
    def get( self ):
        # Make sure it's me
        user = self.get_user( )
        if not user or user.username != "rggibson":
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        # Recalculate num_pbs for every game
        q = db.Query( games.Games )
        q.ancestor( games.key() )
        for game_model in q.run( limit=100000 ):
            q2 = db.Query( runs.Runs, projection=('username', 'category'),
                           distinct=True )
            q2.ancestor( runs.key() )
            q2.filter( 'game =', game_model.game )
            game_model.num_pbs = q2.count( limit=1000 )
            game_model.put( )

        self.write( "FixerUpper complete!\n" )
