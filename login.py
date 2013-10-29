# login.py
# Author: Richard Gibson
#
# Handles user logins.  Upon successful login, a 'user_id' cookie is set that
# stores the user's name and an encrypted authentication token (see 
# util.make_secure_val).  The user is then redirected to their previous page
# that is indicated by the 'from' query parameter.
#

import handler
import runners
import util

class Login( handler.Handler ):
    def get( self ):
        return_url = self.request.get( 'from' )
        if not return_url:
            return_url = "/"

        self.render( "login.html", return_url=return_url )

    def post( self ):
        username = self.request.get( 'username' )
        password = self.request.get( 'password' )
        return_url = self.request.get( 'from' )
        if not return_url:
            return_url = "/"
        username_code = util.get_code( username )

        # Find the user in the database
        user = runners.Runners.get_by_key_name( username_code,
                                                parent=runners.key() )
        if not user:
            self.render( "login.html", username=username, 
                         return_url=return_url, error="Invalid login" )
            return

        # Check for valid password
        if util.valid_pw( username_code, password, user.password ):
            self.login( username_code )
            self.redirect( return_url )
        else:
            self.render( "login.html", username=username, 
                         return_url=return_url, error="Invalid login" )
