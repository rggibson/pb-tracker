# main.py
# Author: Richard Gibson
#
# Launch point for the app.  Defines all of the URL handles, including a
# default handler for all non-matching URLs.
#

import webapp2
import front
import signup
import login
import logout
import submit
import presubmit
import runnerpage
import gamepage
import handler
import gamelist
import runnerlist
import deleterun
import updatebkt
import xmlpage
import edit_table
import asup
import cleanup_games
import cleanup_games_now
import change_categories
import fixerupper

DEBUG = False

class Default( handler.Handler ):
    def get( self, url ):
        user = self.get_user()
        self.error( 404 )
        self.render( "404.html", user=user )

MY_RE = r'([a-zA-Z0-9_+-]+)'
RUN_RE = r'([0-9]+)'
app = webapp2.WSGIApplication( [ ('/', front.Front), 
                                 ('/signup/?', signup.Signup),
                                 ('/login/?', login.Login),
                                 ('/logout/?', logout.Logout),
                                 ('/submit/' + MY_RE + '/?', submit.Submit),
                                 ('/submit/?', presubmit.PreSubmit),
                                 ('/games(?:\.json)?/?', gamelist.GameList),
                                 ('/runners(?:\.json)?/?', 
                                  runnerlist.RunnerList),
                                 ('/runner/' + MY_RE + '(?:\.json)?/?', 
                                  runnerpage.RunnerPage),
                                 ('/runner/' + MY_RE + '/edit-table/?',
                                  edit_table.EditTable),
                                 ('/game/' + MY_RE + '/update-bkt/?', 
                                  updatebkt.UpdateBkt),
                                 ('/game/' + MY_RE + '(?:\.json)?/?', 
                                  gamepage.GamePage),
                                 ('/delete/' + RUN_RE + '/?', 
                                  deleterun.DeleteRun),
                                 ('/faq/?', xmlpage.XmlPage),
                                 ('/blog/?', xmlpage.XmlPage),
                                 ('/asup/?', asup.Asup),
                                 ('/cleanup-games', 
                                  cleanup_games.CleanupGames),
                                 ('/cleanup-games-now', 
                                  cleanup_games_now.CleanupGamesNow),
                                 ('/change-categories', 
                                  change_categories.ChangeCategories),
#                                 ('/fixerupper', fixerupper.FixerUpper),
                                 ('/' + r'(.*)', Default) ],
                               debug=DEBUG)
