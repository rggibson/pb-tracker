# gamelist.py
# Author: Richard Gibson
#
# Similar to `runnerlist.py`, but lists games instead of runners.
#

import handler
import logging

from google.appengine.runtime import DeadlineExceededError

class GameList( handler.Handler ):
    def get( self ):
        try:
            user = self.get_user( )
            if user == self.OVER_QUOTA_ERROR:
                user = None

            gamelist = self.get_gamelist( )
            if gamelist == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
            elif self.format == 'html':
                self.render( "games.html", user=user, gamelist=gamelist )
            elif self.format == 'json':
                self.render_json( gamelist )

        except DeadlineExceededError, msg:
            logging.error( msg )
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )
