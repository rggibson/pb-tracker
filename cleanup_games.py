# cleanup_games.py
# Author: Richard Gibson
#
# A cron job that clean up games and categories from the database that no
# longer have any runs.  This can occur when someone submits a run for a new
# game or category, and then later edits or deletes the run.  Without this
# cleanup job, old games and categories will linger in the database and appear
# in the ui-autocomplete inputs on the submission page. 
#

import cleanup_games_base

class CleanupGames( cleanup_games_base.CleanupGamesBase ):
    def get( self ):
        self.cleanup_games( )
