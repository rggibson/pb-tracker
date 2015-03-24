# gamelist.py
# Author: Richard Gibson
#
# Similar to `runnerlist.py`, but lists games instead of runners.
#

import handler

class GameList( handler.Handler ):
    def get( self ):
        user = self.get_user( )
        if user == self.OVER_QUOTA_ERROR:
            user = None

        gamelist = self.get_gamelist( )

        if self.format == 'html':
            self.render( "games.html", user=user, gamelist=gamelist )
        elif self.format == 'json':
            self.render_json( gamelist )
