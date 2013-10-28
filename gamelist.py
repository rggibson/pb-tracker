import handler

class GameList( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        gamelist = self.get_gamelist( )

        self.render( "games.html", user=user, gamelist=gamelist )
