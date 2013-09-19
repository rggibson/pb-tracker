import webapp2
import front
import signup
import login
import logout
import submit
import runnerpage
import gamepage
import handler
import games

DEBUG = True

class Error( handler.Handler ):
    def get( self ):
        user = self.get_user()
        self.error( 404 )
        self.render( "404.html", user=user )

MY_RE = r'([a-zA-Z0-9_-]+)'
app = webapp2.WSGIApplication( [ ('/', front.Front), 
                                 ('/signup', signup.Signup),
                                 ('/login', login.Login),
                                 ('/logout', logout.Logout),
                                 ('/submit', submit.Submit),
                                 ('/games', games.Games),
                                 ('/runner/' + MY_RE, runnerpage.RunnerPage),
                                 ('/game/' + MY_RE, gamepage.GamePage),
                                 ('/' + r'.*', Error)],
                               debug=DEBUG)
