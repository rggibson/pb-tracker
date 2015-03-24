# fixerupper.py
# Author: Richard Gibson
#
# An admin-only handler for managing one-time clean-up tasks.  Currently, this
# is the best way to clean up some of the extra games and categories that have
# been submitted that (hopefully unintentionally) have duplicated other
# games.Games entries.  I should probably come up with a better way to 
# manage this, but this class will do the job for now.  I've also used this 
# to fix some of the database entries after a bug was discovered (like bad
# dates on runs). 
# 

import games
import runs
import util
import handler
import json
import logging

from google.appengine.ext import db
from google.appengine.runtime import apiproxy_errors

class FixerUpper( handler.Handler ):
    def get( self ):
        # Make sure it's me
        user = self.get_user( )
        if not user:
            self.error( 404 )
            self.render( "404.html", user=user )
            return
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return
        elif user.username != "rggibson":
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        # Convert seconds to float
        count = 0
        try:
            q = db.Query( runs.Runs )
            q.ancestor( runs.key() )
            for run in q.run( limit=1000000 ):
                count += 1
                if not isinstance( run.seconds, float ):
                    run.seconds = float( run.seconds )
                    run.put( )
        except apiproxy_errors.OverQuotaError, message:
            logging.error( message )
            self.write( "Over quota error caught after "
                        + str( count ) + "runs:<br>" + message )
            return

        self.write( "FixerUpper complete!<br>" )
