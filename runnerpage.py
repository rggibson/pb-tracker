# runnerpage.py
# Author: Richard Gibson
#
# Renders individual runner pages at /runner/<username_code>, where 
# username_code is the runner's username converted to lower case with most 
# non-alphanumeric characters replaced with dashes (see util.get_code).  
#
# There are two versions of runner pages.  The default version renders a 
# table of PBs submitted by the runner, ordered by number of runs.  
# The content of this table is aquired through handler.get_pblist() that 
# returns a list of dictionaries, one for each game.  For each dictionary d, 
# d['infolist'] is itself another list of dictionaries, one for each category 
# the runner has run for the given game.  These dictionaries are acquired 
# through handler.get_runinfo(). The alternative runner page is rendered 
# given the query string '?q=view-all' and lists all of the runner's runs, 
# ordered by run date, acquired through handler.get_runlist_for_runner().  
# This function returns its own list of dictionaries.
#

import handler
import logging
import json
import util

class RunnerPage( handler.Handler ):
    def get( self, username_code ):
        user = self.get_user( )
        q = self.request.get( 'q', default_value=None )

        # Make sure the runner exists
        runner = self.get_runner( username_code )
        if runner is None:
            self.error( 404 )
            self.render( "404.html", user=user )
            return
        username = runner.username
        gravatar = util.get_gravatar_url( runner.gravatar, size=120 )

        if q == 'view-all':
            # List all runs for this runner
            runlist = self.get_runlist_for_runner( username )
            if self.format == 'html':
                self.render( "listruns.html", user=user, runner=runner,
                             username_code=username_code, runlist=runlist,
                             gravatar=gravatar )
            elif self.format == 'json':
                self.render_json( runlist )
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

            if runner.visible_columns:
                visible_columns = json.loads( runner.visible_columns )
            else:
                visible_columns = util.get_default_visible_columns( )

            if self.format == 'html':
                self.render( "runnerpage.html", user=user, runner=runner,
                             username_code=username_code, pblist=pblist,
                             gravatar=gravatar, 
                             visible_columns=visible_columns )
            elif self.format == 'json':
                self.render_json( pblist )
