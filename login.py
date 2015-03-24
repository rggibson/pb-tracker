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

        ( valid, errors ) = self.is_valid_login( username, password )
        if not valid:
            if errors.get( user_error ) == 'Over quota error':
                self.error( 403 )
                self.render( "403.html" )
            else:
                self.render( "login.html", username=username,
                             return_url=return_url, **errors )
        else:
            # Success!
            self.login( util.get_code( username ) )
            self.redirect( return_url )
