# gamelist.py
# Author: Richard Gibson
#
# Similar to `runnerlist.py`, but lists games instead of runners.
#

import handler
import logging

from google.appengine.runtime import DeadlineExceededError

class GameList( handler.Handler ):
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

            has_prev = True
            if page_num == 1:
                has_prev = False
            d = self.get_gamelist( page_num )
            if d == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
            elif self.format == 'html':
                self.render( "games.html", user=user, gamelist=d['gamelist'],
                             has_prev=has_prev, has_next=d['has_next'],
                             page_num=d['page_num'] )
            elif self.format == 'json':
                self.render_json( d['gamelist'] )

        except DeadlineExceededError, msg:
            logging.error( msg )
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )
