# runnerlist.py
# Author: Richard Gibson
#
# Lists all runners (users) that have signed up on PB Tracker, sorted by the 
# number of PBs submitted.  This is achieved by calling 
# handler.get_runnerlist( ) that returns a sorted list of dictionaries 
# containing the relevant information. 
#

import handler
import logging

from google.appengine.runtime import DeadlineExceededError

class RunnerList( handler.Handler ):
    def get( self ):
        try:
            user = self.get_user( )
            if user == self.OVER_QUOTA_ERROR:
                user = None

            page_num = self.request.get( 'page', default_value=1 )
            try:
                page_num = int( page_num )
            except ValueError:
                # Default to first page
                page_num = 1

            res = self.get_runnerlist( page_num )

            if res == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
            elif self.format == 'html':
                self.render( "runners.html",
                             user=user,
                             runnerlist=res['runnerlist'],
                             has_next=res['has_next'],
                             page_num=res['page_num'] )
            elif self.format == 'json':
                self.render_json( res['runnerlist'] )

        except DeadlineExceededError, msg:
            logging.error( msg )
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )
