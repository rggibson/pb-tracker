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
#import fixerupper
import updatebkt

DEBUG = True

class Error( handler.Handler ):
    def get( self ):
        user = self.get_user()
        self.error( 404 )
        self.render( "404.html", user=user )

MY_RE = r'([a-zA-Z0-9_-]+)'
RUN_RE = r'([0-9]+)'
app = webapp2.WSGIApplication( [ ('/', front.Front), 
                                 ('/signup', signup.Signup),
                                 ('/login', login.Login),
                                 ('/logout', logout.Logout),
                                 ('/submit', submit.Submit),
                                 ('/games', gamelist.GameList),
                                 ('/runners', runnerlist.RunnerList),
                                 ('/runner/' + MY_RE, runnerpage.RunnerPage),
                                 ('/game/' + MY_RE + '/update-bkt', 
                                  updatebkt.UpdateBkt),
                                 ('/game/' + MY_RE, gamepage.GamePage),
                                 ('/delete/' + RUN_RE, deleterun.DeleteRun),
#                                 ('/fixerupper', fixerupper.FixerUpper),
                                 ('/' + r'.*', Error) ],
                               debug=DEBUG)
