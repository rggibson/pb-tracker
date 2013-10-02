import runhandler
import runs
import util

class DeleteRun( runhandler.RunHandler ):
    def get( self, run_id ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        # Get the run
        run = runs.Runs.get_by_id( long( run_id ), parent=runs.key() )
        if not run or run.username != user.username:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        self.render( "deleterun.html", user=user, run=run, 
                     game_code=util.get_code( run.game ),
                     username_code=util.get_code( user.username ),
                     time=util.seconds_to_timestr( run.seconds ) )

    def post( self, run_id ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        # Get the run
        run = runs.Runs.get_by_id( long( run_id ), parent=runs.key() )
        if not run or run.username != user.username:
            self.error( 404) 
            self.render( "404.html", user=user )
            return

        # Delete the run
        run.delete( )

        # Update memcache
        old_run = dict( game = run.game, category = run.category,
                        seconds = run.seconds )
        self.update_cache_run_by_id( run_id, None )
        ( pblist, fresh ) = self.get_pblist( user.username )
        if not fresh:
            self.update_pblist_delete( pblist, user, old_run )
        self.update_rundict_delete( user, old_run )
        num_runs = self.num_runs( user.username, run.game, run.category, 1 )
        if num_runs <= 0:
            self.update_gamelist_delete( old_run )
            self.update_runnerlist_delete( user )

        # Update runlist for runner in memcache
        ( runlist, fresh ) = self.get_runlist_for_runner( user.username )
        if not fresh:
            for i, run in enumerate( runlist ):
                if run[ 'run_id' ] == run_id:
                    del runlist[ i ]
                    self.update_cache_runlist_for_runner( user.username,
                                                          runlist )
                    break

        # Done with deletion
        self.redirect( "/runner/" + util.get_code( user.username )
                       + "?q=view-all" )
