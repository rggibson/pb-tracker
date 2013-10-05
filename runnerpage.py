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
        username = self.get_username( username_code )
        if not username:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        if q == 'view-all':
            # List all runs for this runner
            runlist = self.get_runlist_for_runner( username )
            self.render( "listruns.html", user=user, username=username,
                         username_code=username_code, runlist=runlist )
        else:
            # By default, list pbs for this runner
            pblist = self.get_pblist( username )
            # We are also going to list the best known times for each game run.
            # Let's gather those times here and add them to the pblist info
            for pb in pblist:
                game_model = self.get_game_model( pb['game_code'] )
                if game_model is None:
                    logging.error( "No game_model for game " + pb['game'] )
                    self.render( "runnerpage.html", user=user, 
                                 username=username,
                                 username_code=username_code, pblist=pblist )
                    return
                gameinfolist = json.loads( game_model.info )
                for runinfo in pb['infolist']:
                    # Find the matching gameinfo
                    for gameinfo in gameinfolist:
                        if gameinfo['category'] == runinfo['category']:
                            try:
                                runinfo['bk_runner'] = gameinfo['bk_runner']
                                runinfo['bk_time'] = util.seconds_to_timestr(
                                    gameinfo['bk_seconds'] )
                                runinfo['bk_video'] = gameinfo['bk_video']
                            except KeyError:
                                runinfo['bk_runner'] = None
                                runinfo['bk_time'] = None
                                runinfo['bk_video'] = None
                            break

            self.render( "runnerpage.html", user=user, username=username,
                         username_code=username_code, pblist=pblist )
