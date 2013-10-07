import handler
import logging
import json
import util

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
        runner = self.get_runner( username_code )
        if runner is None:
            self.error( 404 )
            self.render( "404.html", user=user )
            return
        username = runner.username
        gravatar = util.get_gravatar_url( runner.gravatar )

        if q == 'view-all':
            # List all runs for this runner
            runlist = self.get_runlist_for_runner( username )
            self.render( "listruns.html", user=user, runner=runner,
                         username_code=username_code, runlist=runlist,
                         gravatar=gravatar )
        else:
            # By default, list pbs for this runner
            pblist = self.get_pblist( username )
            # We are also going to list the best known times for each game.
            # Let's gather those times here and add them to the pblist info.
            for pb in pblist:
                game_model = self.get_game_model( pb['game_code'] )
                if game_model is None:
                    logging.error( "No game_model for game " + pb['game'] )
                    continue
                gameinfolist = json.loads( game_model.info )
                for runinfo in pb['infolist']:
                    # Find the matching gameinfo
                    for gameinfo in gameinfolist:
                        if gameinfo['category'] == runinfo['category']:
                            runinfo['bk_runner'] = gameinfo.get( 'bk_runner' )
                            runinfo['bk_time'] = util.seconds_to_timestr(
                                gameinfo.get( 'bk_seconds' ) )
                            runinfo['bk_video'] = gameinfo.get( 'bk_video' )
                            break

            self.render( "runnerpage.html", user=user, runner=runner,
                         username_code=username_code, pblist=pblist,
                         gravatar=gravatar )
