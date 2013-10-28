import handler

class RunnerList( handler.Handler ):
    def get( self ):
        user = self.get_user( )

        runnerlist = self.get_runnerlist( )

        self.render( "runners.html", user=user, runnerlist=runnerlist )
