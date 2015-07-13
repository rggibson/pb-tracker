# runnerpage.py
# Author: Richard Gibson
#
# Renders individual runner pages at /runner/<username_code>, where 
# username_code is the runner's username converted to lower case with most 
# non-alphanumeric characters replaced with dashes (see util.get_code).  
#
# There are two versions of runner pages.  The default version renders a 
# table of PBs submitted by the runner.
# The content of this table is aquired through handler.get_pblist() that 
# returns a list of dictionaries, one for each game.  For each dictionary d, 
# d['infolist'] is itself another list of dictionaries, one for each category 
# the runner has run for the given game.
# The alternative runner page is rendered 
# given the query string '?q=view-all' and lists all of the runner's runs, 
# ordered by run date, acquired through handler.get_runlist_for_runner().  
# This function returns its own list of dictionaries.
#

import handler
import logging
import json
import util

from google.appengine.runtime import DeadlineExceededError

class RunnerPage( handler.Handler ):
    def get( self, username_code ):
        try:
            user = self.get_user( )
            if user == self.OVER_QUOTA_ERROR:
                user = None
            q = self.request.get( 'q', default_value=None )
            t = self.request.get( 't', default_value=None )
            show_all = False
            page_num = 1
            if t == 'show-all':
                show_all = True
            else:
                # Grab the page num
                page_num = self.request.get( 'page', default_value=1 )
                try:
                    page_num = int( page_num )
                except ValueError:
                    page_num = 1

            # Make sure the runner exists
            runner = self.get_runner( username_code )
            if runner is None:
                self.error( 404 )
                self.render( "404.html", user=user )
                return
            if runner == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                if self.format == 'html':
                    self.render( "403.html", user=user )
                return
            username = runner.username
            gravatar = util.get_gravatar_url( runner.gravatar, size=120 )

            if q == 'view-all':
                # List all runs for this runner
                res = self.get_runlist_for_runner( username, page_num )
                if res == self.OVER_QUOTA_ERROR:
                    self.error( 403 )
                    self.render( "403.html", user=user )
                elif self.format == 'html':
                    self.render( "listruns.html", user=user, runner=runner,
                                 username_code=username_code,
                                 runlist=res['runlist'],
                                 page_num=res['page_num'],
                                 has_next=res['has_next'],
                                 has_prev=(res['page_num'] > 1),
                                 gravatar=gravatar )
                elif self.format == 'json':
                    self.render_json( res['runlist'] )
            else:
                # By default, list pbs for this runner
                res = self.get_pblist( username, page_num, show_all )
                if res == self.OVER_QUOTA_ERROR:
                    self.error( 403 )
                    self.render( "403.html", user=user )
                    return
                # We are also going to list the best known times for each game.
                # Let's gather those times here and add them to the pblist
                # info.
                pblist = res['pblist']
                for pb in pblist:
                    game_model = self.get_game_model( pb['game_code'] )
                    if game_model is None:
                        logging.error( "No game_model for game " + pb['game'] )
                        continue
                    if game_model == self.OVER_QUOTA_ERROR:
                        self.error( 403 )
                        self.render( "403.html", user=user )
                        return
                    gameinfolist = json.loads( game_model.info )
                    for runinfo in pb['infolist']:
                        # Find the matching gameinfo
                        for gameinfo in gameinfolist:
                            if gameinfo['category'] == runinfo['category']:
                                runinfo['bk_runner'] = gameinfo.get(
                                    'bk_runner' )
                                runinfo['bk_time'] = util.seconds_to_timestr(
                                    gameinfo.get( 'bk_seconds' ) )
                                runinfo['bk_video'] = gameinfo.get(
                                    'bk_video' )
                                break

                if runner.visible_columns:
                    visible_columns = json.loads( runner.visible_columns )
                else:
                    visible_columns = util.get_default_visible_columns( )

                if self.format == 'html':
                    self.render( "runnerpage.html", user=user, runner=runner,
                                 username_code=username_code, pblist=pblist,
                                 gravatar=gravatar, page_num=res['page_num'],
                                 has_next=res['has_next'],
                                 has_prev=( res['page_num'] > 1 ),
                                 visible_columns=visible_columns,
                                 show_all=res['show_all'] )
                elif self.format == 'json':
                    self.render_json( pblist )

        except DeadlineExceededError, msg:
            logging.error( msg )
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )
