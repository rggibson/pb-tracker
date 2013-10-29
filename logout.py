# logout.py
# Author: Richard Gibson
#
# Logs the user out and redirects them back to where they came from as
# specified by the 'from' query parameter.
#

import handler

class Logout( handler.Handler ):
    def get( self ):
        return_url = self.request.get( 'from' )
        if not return_url:
            return_url = "/"
        # Clear login cookie 
        cookie = 'user_id=;Path=/'
        self.response.headers.add_header( 'Set-Cookie', cookie )
        self.redirect( return_url )
