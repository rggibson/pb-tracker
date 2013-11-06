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
import runnerpage
import gamepage
import handler
import gamelist
import runnerlist
import deleterun
import updatebkt
import faq
import edit_table
import asup
import fixerupper

DEBUG = True

class Default( handler.Handler ):
    def get( self, url ):
        user = self.get_user()
        self.error( 404 )
        self.render( "404.html", user=user )

MY_RE = r'([a-zA-Z0-9_-]+)'
RUN_RE = r'([0-9]+)'
app = webapp2.WSGIApplication( [ ('/', front.Front), 
                                 ('/signup/?', signup.Signup),
                                 ('/login/?', login.Login),
                                 ('/logout/?', logout.Logout),
                                 ('/submit/?', submit.Submit),
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
                                 ('/faq/?', faq.Faq),
                                 ('/asup/?', asup.Asup),
                                 ('/fixerupper', fixerupper.FixerUpper),
                                 ('/' + r'(.*)', Default) ],
                               debug=DEBUG)
