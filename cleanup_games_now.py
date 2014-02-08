# cleanup_games_now.py
# Author: Richard Gibson
#
# Same thing as cleanup_games.py, except this is not a cron job and instead
# is invoked manually.
#

import cleanup_games_base

class CleanupGamesNow( cleanup_games_base.CleanupGamesBase ):
    def get( self ):
        # Make sure we are a mod
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return
        if not user.is_mod:
            self.error( 404 )
            self.render( "404.html", user=user )
            return
        
        self.cleanup_games( )
