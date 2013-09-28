import handler

class RunnerList( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        # Set this page to be the return page after a login/logout/signup
        self.set_return_url('/runners')
        
        ( runnerlist, fresh ) = self.get_runnerlist( )

        self.render( "runners.html", user=user, runnerlist=runnerlist )
