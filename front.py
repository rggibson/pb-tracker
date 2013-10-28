import handler

class Front( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        self.render( "front.html", user=user )
