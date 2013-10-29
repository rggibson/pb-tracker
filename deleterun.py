# deleterun.py
# Author: Richard Gibson
#
# Handles deletion of runs previously submitted.  Removes the deleted run
# from the datastore and calls the appropriate memcache update functions.  
#

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
        run = self.get_run_by_id( run_id )
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

        # Update games
        delta_num_pbs = 0
        num_runs = self.num_runs( user.username, run.game, run.category, 1 )
        if num_runs == 0:
            delta_num_pbs = -1
        self.update_games_delete( old_run, delta_num_pbs )

        # Must update runinfo before pblist and gamepage because pblist and
        # gamepage rely on accurate runinfo
        self.update_runinfo_delete( user, old_run )
        self.update_pblist_delete( user, old_run )
        self.update_gamepage_delete( user, old_run )
        self.update_user_has_run_delete( user, old_run )
        if num_runs <= 0:
            self.update_gamelist_delete( old_run )
            self.update_runnerlist_delete( user )

        # Update runlist for runner in memcache
        runlist = self.get_runlist_for_runner( user.username, 
                                               no_refresh=True )
        if runlist:
            for i, run in enumerate( runlist ):
                if run[ 'run_id' ] == run_id:
                    del runlist[ i ]
                    self.update_cache_runlist_for_runner( user.username,
                                                          runlist )
                    break

        # Update last run
        last_run = self.get_last_run( user.username, no_refresh=True )
        if last_run is not None and last_run.key( ).id( ) == long( run_id ):
            self.update_cache_last_run( user.username, None )

        # Done with deletion
        self.redirect( "/runner/" + util.get_code( user.username )
                       + "?q=view-all" )
