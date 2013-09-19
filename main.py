import webapp2
import front
import signup
import login
import logout
import submit
import runnerpage
import gamepage

DEBUG = True

MY_RE = r'([a-zA-Z0-9_-]+)'
app = webapp2.WSGIApplication( [ ('/', front.Front), 
                                 ('/signup', signup.Signup),
                                 ('/login', login.Login),
                                 ('/logout', logout.Logout),
                                 ('/submit', submit.Submit),
                                 ('/runner/' + MY_RE, runnerpage.RunnerPage),
                                 ('/game/' + MY_RE, gamepage.GamePage) ],
                               debug=DEBUG)
