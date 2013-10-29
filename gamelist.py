# gamelist.py
# Author: Richard Gibson
#
# Similar to `runnerlist.py`, but lists games instead of runners.
#

import handler

class GameList( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        gamelist = self.get_gamelist( )

        self.render( "games.html", user=user, gamelist=gamelist )
