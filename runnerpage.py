import handler

class RunnerPage( handler.Handler ):
    def get( self, username_code ):
        user = self.get_user( )
        q = self.request.get( 'q', default_value=None )

        # Set this page to be the return page after a login/logout/signup
        return_url = '/runner/' + username_code
        if q:
            return_url += '?q=' + str( q )
        self.set_return_url( return_url )

        # Make sure the runner exists
        username = self.get_username( username_code )
        if not username:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        if q == 'view-all':
            # List all runs for this runner
            ( runlist, fresh ) = self.get_runlist_for_runner( username )
            self.render( "listruns.html", user=user, username=username,
                         username_code=username_code, runlist=runlist )
        else:
            # By default, list pbs for this runner
            pblist = self.get_pblist( username )
            self.render( "runnerpage.html", user=user, username=username,
                         username_code=username_code, pblist=pblist )
