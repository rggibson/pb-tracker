# fixerupper.py
# Author: Richard Gibson
#
# An admin-only handler for managing one-time clean-up tasks.  Currently, this
# is the best way to clean up some of the extra games and categories that have
# been submitted that (hopefully unintentionally) have duplicated other
# games.Games entries.  I should probably come up with a better way to 
# manage this, but this class will do the job for now.  I've also used this 
# to fix some of the database entries after a bug was discovered (like bad
# dates on runs). 
# 

import games
import runs
import util
import handler
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

        # Mark all of the games that were originally uploaded
        f = open( 'json/import_games.json', 'r' )
        iglist = json.loads( f.read( ) )
        f.close( )

        for d in iglist:
            game_code = util.get_code( d['game'] )
            game_model = self.get_game_model( game_code )
            if game_model is None:
                self.write( 'No game model for game ' + d['game'] + '<br>' )
                continue
            gameinfolist = json.loads( game_model.info )
            modified = False
            for gameinfo in gameinfolist:
                category = gameinfo.get( 'category' )
                if category in d['categories']:
                    gameinfo['is_base_category'] = True
                    modified = True
                    self.write( d['game'] + ' - ' + category + '<br>' )
            if modified:
                game_model.info = json.dumps( gameinfolist )
                game_model.put( )
                self.update_cache_game_model( game_code, game_model )

        # # Recalculate num_pbs for every game
        # q = db.Query( games.Games )
        # q.ancestor( games.key() )
        # for game_model in q.run( limit=100000 ):
        #     q2 = db.Query( runs.Runs, projection=('username', 'category'),
        #                    distinct=True )
        #     q2.ancestor( runs.key() )
        #     q2.filter( 'game =', game_model.game )
        #     num_pbs = q2.count( limit=1000 )
        #     if game_model.num_pbs != num_pbs:
        #         self.write( game_model.game + ": " + str( game_model.num_pbs )
        #                     + " -> " + str( num_pbs ) + "<br>" )
        #         game_model.num_pbs = num_pbs
        #         game_model.put( )
        #         # Update memcache
        #         self.update_cache_game_model( util.get_code( game_model.game ),
        #                                       game_model )
        #         self.update_cache_gamelist( None )

        # # Recalculate num_pbs for every runner
        # q = db.Query( runners.Runners )
        # q.ancestor( runners.key() )
        # for runner in q.run( limit=100000 ):
        #     q2 = db.Query( runs.Runs, projection=('game', 'category'),
        #                    distinct=True )
        #     q2.ancestor( runs.key() )
        #     q2.filter( 'username =', runner.username )
        #     num_pbs = q2.count( limit=1000 )
        #     if num_pbs == 0 or runner.num_pbs != num_pbs:
        #         self.write( runner.username + ": " + str( runner.num_pbs )
        #                     + " -> " + str( num_pbs ) + "<br>" )
        #         runner.num_pbs = num_pbs
        #         runner.put( )
        #         # Update memcache
        #         self.update_cache_runner( util.get_code( runner.username ),
        #                                   runner )
        #         self.update_cache_runnerlist( None )

        self.write( "FixerUpper complete!<br>" )
