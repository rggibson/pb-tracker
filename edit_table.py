# edit_table.py
# Author: Richard Gibson
#
# Handles user editing of PB table columns through a simple set of 
# check boxes.
#

import handler
import runners
import util
import json

class EditTable( handler.Handler ):
    def get( self, username_code ):
        user = self.get_user( )

        # Make sure this is the correct user
        if user is None or util.get_code( user.username ) != username_code:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        # Get the stored visible columns, or get the default ones 
        if user.visible_columns:
            visible_columns = json.loads( user.visible_columns )
        else:
            visible_columns = util.get_default_visible_columns( )

        self.render( "edit_table.html", user=user, username_code=username_code,
                     visible_columns=visible_columns )

    def post( self, username_code ):
        user = self.get_user( )

        # Make sure this is the correct user
        if user is None or util.get_code( user.username ) != username_code:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        # Get the visible columns
        visible_columns = util.get_default_visible_columns( )
        for key in visible_columns:
            checked = self.request.get( key + '_visible', default_value="no" )
            if checked == "yes":
                visible_columns[ key ] = True
            else:
                visible_columns[ key ] = False
        
        # Store
        user.visible_columns = json.dumps( visible_columns )
        user.put( )

        # Update memcache
        self.update_cache_runner( username_code, user )

        # That's all
        self.redirect( "/runner/" + username_code )
