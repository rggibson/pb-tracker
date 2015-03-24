# runnerlist.py
# Author: Richard Gibson
#
# Lists all runners (users) that have signed up on PB Tracker, sorted by the 
# number of PBs submitted.  This is achieved by calling 
# handler.get_runnerlist( ) that returns a sorted list of dictionaries 
# containing the relevant information. 
#

import handler

class RunnerList( handler.Handler ):
    def get( self ):
        user = self.get_user( )
        if user == self.OVER_QUOTA_ERROR:
            user = None

        runnerlist = self.get_runnerlist( )

        if runnerlist == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html", user=user )
        elif self.format == 'html':
            self.render( "runners.html", user=user, runnerlist=runnerlist )
        elif self.format == 'json':
            self.render_json( runnerlist )
