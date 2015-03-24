# presubmit.py
# Author: Richard Gibson
#
# Renders a simple form that asks the user which game he or she is submitting
# the run for.  This was added to try to reduce load on having to query
# for all games and categories at once in order to fill in the auto-complete
# inputs.
#

import runhandler
import util
import logging
import runs
import json
import games

from operator import itemgetter
from datetime import date
from google.appengine.ext import db

class PreSubmit( runhandler.RunHandler ):
    def get( self ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return

        params = dict( user=user )
                    
        # Grab all of the games for autocompleting
        params['games'] = self.get_gamelist( get_num_pbs=False )
        if params['games'] == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html", user=user )
        else:
            self.render( "presubmit.html", **params )

    def post( self ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return

        game = self.request.get( 'game' )

        params = dict( user = user, game = game )

        valid = True

        # Make sure the game doesn't already exist under a similar name
        game_code = util.get_code( game )
        game_model = self.get_game_model( game_code )
        if game_model == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html", user=user )
            return        
        if not game_code:
            params['game_error'] = "Game cannot be blank"
            valid = False
        elif game_model is not None and game != game_model.game:
            params['game_error'] = ( "Game already exists under [" 
                                     + game_model.game + "] (case sensitive)."
                                     + " Hit submit again to confirm." )
            params['game'] = game_model.game
            valid = False
        elif not games.valid_game_or_category( game ):
            params['game_error'] = ( "Game name must not use any 'funny'"
                                     + " characters and can be up to 100 "
                                     + "characters long" )
            valid = False
            
        if not valid:
            # Grab all of the games for autocompleting
            params['games'] = self.get_gamelist( get_num_pbs=False )   
            if params['games'] == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
            else:
                self.render( "presubmit.html", **params )
            return

        if game_model is None:
            # Add the game to the database
            valid = self.put_new_game( game )
            if not valid:
                params['game_error'] = ( "Failed to process game with name ["
                                         + game + "] (unknown error)" )

        if valid:
            self.redirect( "/submit/" + game_code + '/' )
        else:
            # Grab all of the games for autocompleting
            params['games'] = self.get_gamelist( get_num_pbs=False )
            if params['games'] == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
            else:
                self.render( "presubmit.html", **params )
            return
