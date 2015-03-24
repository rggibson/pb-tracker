
# cleanup_games_base.py
# Author: Richard Gibson
#
# A base class that clean up games and categories from the database that no
# longer have any runs.  This can occur when someone submits a run for a new
# game or category, and then later edits or deletes the run.  Without this
# cleanup job, old games and categories will linger in the database and appear
# in the ui-autocomplete inputs on the submission page. 
#

import games
import runs
import util
import handler
import json
import logging

from google.appengine.ext import db

class CleanupGamesBase( handler.Handler ):
    def cleanup_games( self ):
        # Grab all of the categories, indexed by game
        categories = self.get_categories( )
        if categories is None:
            return
        categories_modified = False

        games_to_delete = [ ]
        for game, categorylist in categories.iteritems( ):
            # Grab the game model
            game_code = util.get_code( game )
            game_model = self.get_game_model( game_code )
            gameinfolist = json.loads( game_model.info )
            game_model_modified = False
            glist = [ ( i, gameinfo ) 
                      for i, gameinfo in enumerate( gameinfolist ) ]
            for i, gameinfo in reversed( glist ):
                # Leave it if the category is marked as a base category
                if( gameinfo.get( 'is_base_category' )
                    and game != "Luigi's Mansion"
                    and game != "Super Mario Bros.: The Lost Levels"
                    and game != "The Legend of Zelda: A Link to the Past"
                    and game != "Mega Man 9" ):
                    continue
                # Check if there is a run for this game and category
                q = db.Query( runs.Runs, keys_only=True )
                q.ancestor( runs.key() )
                q.filter( 'game =', game )
                q.filter( 'category =', gameinfo['category'] )
                num_runs = q.count( limit=1 )
                if num_runs == 0:
                    # Remove this category
                    del gameinfolist[ i ]
                    logging.info( "Removed " + gameinfo['category'] 
                                   + " from " + game )
                    game_model_modified = True
                    # Remove this category in memcache too
                    for j, category in enumerate( categorylist ):
                        if category == gameinfo['category']:
                            del categorylist[ j ]
                            categories_modified = True
                            break
                    else:
                        logging.error( "ERROR: Could not find in categories" )
            # Remove the game if no more categories exist
            if len( gameinfolist ) == 0:
                game_model.delete( )
                games_to_delete.append( game )
                logging.info( game + " deleted" )
                self.update_cache_game_model( game_code, None )
            # Update database and memcache if necessary
            elif game_model_modified:
                game_model.info = json.dumps( gameinfolist )
                game_model.put( )
                self.update_cache_game_model( game_code, game_model )
        
        # Finally, update categories, gamelists in memcache if necessary
        if categories_modified:
            for game in games_to_delete:
                del categories[ game ]
            self.update_cache_categories( categories )
        gamelist = self.get_gamelist( no_refresh=True, get_num_pbs=True )
        gamelist_snp = self.get_gamelist( no_refresh=True, get_num_pbs=False )
        for game in games_to_delete:
            if gamelist is not None:
                for i, d in enumerate( gamelist ):
                    if d['game'] == game:
                        del( gamelist[ i ] )
                        break
            if gamelist_snp is not None and game in gamelist_snp:
                gamelist_snp.remove( game )
        self.update_cache_gamelist( gamelist, get_num_pbs=True )
        self.update_cache_gamelist( gamelist_snp, get_num_pbs=False )
