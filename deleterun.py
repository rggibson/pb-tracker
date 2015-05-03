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
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return

        # Get the run
        run = self.get_run_by_id( run_id )
        if run == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html", user=user )
            return
        if( not run or 
            ( not user.is_mod and run.username != user.username ) ):
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
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return

        # Get the run
        run = runs.Runs.get_by_id( long( run_id ), parent=runs.key() )
        if( not run or 
            ( not user.is_mod and run.username != user.username ) ):
            self.error( 404 ) 
            self.render( "404.html", user=user )
            return

        # Grab the owner of the run
        if run.username == user.username:
            runner = user
        else:
            runner = self.get_runner( util.get_code( run.username ) )
            if runner == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
                return

        # Delete the run
        run.delete( )

        # Update memcache
        old_run = dict( game = run.game, category = run.category,
                        seconds = run.seconds )
        self.update_cache_run_by_id( run_id, None )

        # Update games, runner
        delta_num_pbs = 0
        num_runs = self.num_runs( runner.username, run.game, run.category, 1 )
        if num_runs == 0:
            delta_num_pbs = -1
        self.update_runner( runner, delta_num_pbs )
        game_model = self.get_game_model( util.get_code( old_run['game'] ) )
        if game_model == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html", user=user )
            return
        self.update_games_delete( game_model, run.category, delta_num_pbs )

        # Must update runinfo before pblist and gamepage because pblist and
        # gamepage rely on accurate runinfo
        self.update_runinfo_delete( runner, old_run )
        self.update_pblist_delete( runner, old_run )
        self.update_gamepage_delete( runner, old_run )
        self.update_user_has_run_delete( runner, old_run )
        if num_runs <= 0:
            self.update_gamelist_delete( old_run )
            self.update_runnerlist_delete( runner )

        # Update runlist for runner in memcache
        cached_runlists = self.get_cached_runlists_for_runner(
            runner.username )
        if cached_runlists is not None:
            found_run = False
            for page_num, res in cached_runlists.iteritems( ):
                if found_run:
                    break
                for i, run in enumerate( res['runlist'] ):
                    if run[ 'run_id' ] == run_id:
                        del cached_runlists[ page_num ]['runlist'][ i ]
                        self.update_cache_runlist_for_runner( runner.username,
                                                              cached_runlists )
                        found_run = True
                        break

        # Update last run
        last_run = self.get_last_run( runner.username, no_refresh=True )
        if last_run == self.OVER_QUOTA_ERROR:
            self.update_cache_last_run( runner.username, None )
        elif last_run is not None and last_run.key( ).id( ) == long( run_id ):
            self.update_cache_last_run( runner.username, None )

        # Done with deletion
        self.redirect( "/runner/" + util.get_code( runner.username )
                       + "?q=view-all" )
