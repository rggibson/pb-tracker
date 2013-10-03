import handler

class GameList( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        # Set this page to be the return page after a login/logout/signup
        self.set_return_url( '/games' )
        
        gamelist = self.get_gamelist( )

        self.render( "games.html", user=user, gamelist=gamelist )
