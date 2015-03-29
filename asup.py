# asup.py
# Author: Richard Gibson
#
# Handler for communication between PB Tracker and an external source, like a
# splits program.  Follows the protocol currently listed here:
# https://docs.google.com/document/d/13UAc4CQTSMBAiEHm7xNdJYT8v27VZY1GJc2aYsaFVu0/edit#
#
# Currently, the gamelist and categories request types are not supported.
# They were removed in an attempt to lighten the load to the site and to
# hopefully reduce downtime that PB Tracker receives.  This two requests in
# particular are pretty hard on the datastore reads, which is a commonly
# exhausted resource.
#

import runhandler
import json
import util

from datetime import datetime
from pytz.gae import pytz

class Asup( runhandler.RunHandler ):
    def get_success_response( self, data=None ):
        response = dict( result='success' )
        if data is not None:
            response['data'] = data
        return response

    def get_fail_response( self, message ):
        return dict( result='fail', message=message )

    def verify_login( self, body ):
        username = body.get( 'username' )
        password = body.get( 'password' )
        if username is None:
            return False, self.get_fail_response( 'No username specified' )
        elif password is None:
            return False, self.get_fail_response( 'No password specified' )
        else:
            ( valid, errors ) = self.is_valid_login( username, password )
            if not valid:
                message = ''
                for error_type, error in errors.iteritems( ):
                    message += error + ' '
                return False, self.get_fail_response( message )

        return True, self.get_success_response( )

    def verify_mod_login( self, body ):
        # First, verify login credentials
        ( valid, response ) = self.verify_login( body )
        if not valid:
            return valid, response

        # Make sure the user is a mod
        username = body.get( 'username' )
        user = self.get_runner( util.get_code( username ) )
        if user == self.OVER_QUOTA_ERROR:
            return False, self.get_fail_response( "PB Tracker is currently "
                                                  + "experiencing an over "
                                                  + "quota limit down time "
                                                  + "period." )
        if not user.is_mod:
            body_type = body.get( 'type' )
            return False, self.get_fail_response( "You must be a mod to use ["
                                                  + body_type + "]." )

        return True, self.get_success_response( )

    def get( self ):
        # By default, return success, a link to the handler, and a link to
        # the protocol doc
        d = dict( type="success",
                  link="http://www.pbtracker.net/asup",
                  spec=( "https://docs.google.com/document/d/"
                         + "13UAc4CQTSMBAiEHm7xNdJYT8v27VZY1GJc2aYsaFVu0/"
                         + "edit#" ) )
        self.render_json( d )

    def post( self ):
        # Fetch the posted data
        body_json = self.request.body        
        try:
            body = json.loads( body_json )
        except ValueError:
            return self.get_fail_response( "Could not parse body to JSON" )

        # Render the response
        try:
            self.render_json( self.get_response( body ) )
        except google.appengine.runtime.DeadlineExceededError:
            return self.get_fail_response( "Server timed out" )

    def get_response( self, body ):
        body_type = body.get( 'type' )

        # Currently 5 types: verifylogin, gamelist, categories, gamecategories
        # and submitrun
        if body_type is None:
            return self.get_fail_response( "No type given." )
        
        elif body_type == 'verifylogin':
            ( valid, response ) = self.verify_login( body )
            return response

        elif body_type == 'gamelist':
            return self.get_fail_response( "Type [" + body_type + "] currently"
                                           + " not supported dynamically, but "
                                           + "you can find a static JSON "
                                           + "response at "
                                           + "https://www.dropbox.com/s/"
                                           + "xnvsmx3mt0i4nbv/gamelist.json?dl"
                                           + "=0" )

        elif body_type == 'categories':
            return self.get_fail_response( "Type [" + body_type + "] currently"
                                           + " not supported dynamically, but "
                                           + "you can find a static JSON "
                                           + "response at "
                                           + "https://www.dropbox.com/s/"
                                           + "irdj4xakh72g541/categories.json?"
                                           + "dl=0" )

        elif body_type == 'modgamelist':
            # First, verify login credentials and that we are a mod
            ( valid, response ) = self.verify_mod_login( body )
            if not valid:
                return response

            # Note that this is a different type of gamelist than the one
            # generated in games.py
            categories = self.get_categories( )
            if categories == self.OVER_QUOTA_ERROR:
                return self.get_fail_response( "PB Tracker is currently "
                                               + "experiencing an over "
                                               + "quota downtime period." )
            d = dict( )
            for game in categories.keys( ):
                d[ util.get_code( game ) ] = game
            return self.get_success_response( data=d )

        elif body_type == 'modcategories':
            # First, verify login credentials and that we are a mod
            ( valid, response ) = self.verify_mod_login( body )
            if not valid:
                return response

            categories = self.get_categories( )
            if categories == self.OVER_QUOTA_ERROR:
                return self.get_fail_response( "PB Tracker is currently "
                                               + "experiencing an over "
                                               + "quota downtime period." )
            d = dict( )
            for game, categorylist in categories.iteritems( ):
                game_code = util.get_code( game )
                for category in categorylist:
                    category_code = util.get_code( category )
                    d[ game_code + ':' + category_code ] = ( game + ' - ' 
                                                             + category )
            return self.get_success_response( data=d )

        elif body_type == 'gamecategories':
            return self.get_fail_response( "Type [" + body_type + "] currently"
                                           + " not supported, sorry." )
#            game_code = body.get( 'game' )
#            game_model = self.get_game_model( game_code )
#            if game_code is None:
#                return self.get_fail_response( 'No game specified' )
#            elif game_model is None:
#                return self.get_fail_response( 'Unknown game [' 
#                                               + game_code + '].' )
#            TODO: elif game_model == self.OVER_QUOTA_ERROR:
#            else:
#                d = dict( )
#                gameinfolist = json.loads( game_model.info )
#                for gameinfo in gameinfolist:
#                    category = gameinfo['category']
#                    d[ util.get_code( category ) ] = category
#                return self.get_success_response( data=d )

        elif body_type == 'submitrun':
            # First, verify login credentials
            ( valid, response ) = self.verify_login( body )
            if not valid:
                return response

            # Grab the params from the body
            username = body.get( 'username' )
            game_code = body.get( 'game' )
            category_code = body.get( 'category' )
            version = body.get( 'version' )
            time = body.get( 'runtime' )
            video = body.get( 'video' )
            notes = body.get( 'comment' )
            splits = body.get( 'splits' )

            # Make sure the game and category exist (can't handle new games
            # and categories just yet)
            if game_code is None:
                return self.get_fail_response( 'No game given' )
            game_model = self.get_game_model( game_code )
            if game_model is None:
                return self.get_fail_response( 'Unknown game [' 
                                               + game_code + '].' )
            if game_model == self.OVER_QUOTA_ERROR:
                return self.get_fail_response( 'PB Tracker is currently over '
                                               + "quota. Please try again "
                                               + "later." )
            if category_code is None:
                return self.get_fail_response( 'No category specified' )
            gameinfolist = json.loads( game_model.info )
            category = None
            for gameinfo in gameinfolist:
                if category_code == util.get_code( gameinfo['category'] ):
                    category = gameinfo['category']
                    break
            if category is None:
                return self.get_fail_response( 'Unknown category [' 
                                               + category_code 
                                               + '] for game [' 
                                               + game_code + '].' )

            # Parse the time into seconds and ensure it is valid
            if time is None:
                return self.get_fail_response( 'No runtime given' )
            ( seconds, time_error ) = util.timestr_to_seconds( time )
            if seconds is None:
                return self.get_fail_response( 'Bad runtime [' + time 
                                               + '] given: ' + time_error )
            # Ensure standard format
            time = util.seconds_to_timestr( seconds )

            # Make sure that the notes are not too long
            if notes is not None and len( notes ) > 140:
                return self.get_fail_response( 'Comment is too long; must be '
                                               + 'at most 140 characters.' )

            # Figure out current date in user's local timezone
            user = self.get_runner( util.get_code( username ) )
            if user == self.OVER_QUOTA_ERROR:
                return False, self.get_fail_response( 
                    "PB Tracker is currently "
                    + "experiencing an over "
                    + "quota limit down time "
                    + "period." )
            if user.timezone:
                tz = pytz.timezone( user.timezone )
                local_today = datetime.now( pytz.utc ).astimezone( tz )
            else:
                # UTC by default
                local_today = datetime.now( pytz.utc )
            date = local_today.date( )

            # Load up the needed parameters and put a new run
            params = dict( user=user,
                           game=game_model.game,
                           game_code=game_code,
                           game_model=game_model,
                           category=category,
                           category_found=True,
                           seconds=seconds,
                           time=time,
                           video=video,
                           version=version,
                           notes=notes,
                           valid=True,
                           date=date,
                           datestr=date.strftime( "%m/%d/%Y" ),
                           is_bkt=False ) 
            if self.put_new_run( params ):
                return self.get_success_response( )
            else:
                if params.get( 'video_error' ):
                    return self.get_fail_response( 'Bad video link [' 
                                                   + video + ']: ' 
                                                   + params[ 'video_error' ] )
                else:
                    return self.get_fail_response( 'Sorry, an unknown error '
                                                   + 'occurred.' )
                    
        return self.get_fail_response( "Unknown type [" + body_type + "]." )
