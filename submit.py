# submit.py
# Author: Richard Gibson
#
# Writes runs submitted by users to the database and updates common queries 
# stored in memcache.  On a successful POST, the run is put in the
# database and several update_memcache functions are run to ensure that the
# memcache is not stale.
#
# submit.py also handles run editing through the '?edit=<run_id>' query string.
# Most of the handling is the same as for submitting a new run, except 
# extra memcache update functions that delete the old run must first be run
# before updating the memcache with the new run.
#
# Note that it is currently not possible to edit the game name of a run.
# These types of edits must instead be deleted and re-submitted.
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

class Submit( runhandler.RunHandler ):
    def get( self, game_code ):
        try:
            user = self.get_user( )
            if not user:
                self.redirect( "/" )
                return
            elif user == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html" )
                return

            params = dict( user=user )

            game_model = self.get_game_model( game_code )
            if game_model is None:
                self.error( 404 )
                self.render( "404.html", user=user )
                return
            if game_model == self.OVER_QUOTA_ERROR:
                self.error( 403 )
                self.render( "403.html", user=user )
                return        

            # Are we editing an existing run?
            run_id = self.request.get( 'edit' )
            if run_id:
                # Grab the run to edit
                run = self.get_run_by_id( run_id )
                if run == self.OVER_QUOTA_ERROR:
                    self.error( 403 )
                    self.render( "403.html", user=user )
                    return
                if not run or ( not user.is_mod 
                                and user.username != run.username ):
                    self.error( 404 )
                    self.render( "404.html", user=user )
                    return
                params[ 'game' ] = run.game
                params[ 'game_code' ] = game_code
                params[ 'category' ] = run.category
                params[ 'time' ] = util.seconds_to_timestr( run.seconds )
                if run.date is not None:
                    params[ 'datestr' ] = run.date.strftime( "%m/%d/%Y" );
                params[ 'run_id' ] = run_id
                if run.video is not None:
                    params[ 'video' ] = run.video
                if run.version is not None:
                    params[ 'version' ] = run.version
                if run.notes is not None:
                    params[ 'notes' ] = run.notes
            else:
                params['game'] = game_model.game
                params['game_code'] = game_code
                params['set_date_to_today'] = True;            
                    
            # Grab all of the categories for autocompleting
            params['categories'] = game_model.categories( )

            self.render( "submit.html", **params )

        except google.appengine.runtime.DeadlineExceededError:
            self.error( 403 )
            self.render( "deadline_exceeded.html", user=user )

    def post( self, game_code ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return
        elif user == self.OVER_QUOTA_ERROR:
            self.error( 403 )
            self.render( "403.html" )
            return

        category = self.request.get( 'category' )
        time = self.request.get( 'time' )
        datestr = self.request.get( 'date' )
        video = self.request.get( 'video' )
        version = self.request.get( 'version' )
        notes = self.request.get( 'notes' )
        is_bkt = self.request.get( 'bkt', default_value="no" )
        if is_bkt == "yes":
            is_bkt = True
        else:
            is_bkt = False
        run_id = self.request.get( 'edit' )

        params = dict( user = user, game_code = game_code,
                       category = category, 
                       time = time, datestr = datestr, video = video, 
                       version = version, notes = notes, run_id = run_id, 
                       is_bkt = is_bkt )

        valid = True

        # Make sure the game already exists
        game_model = self.get_game_model( game_code )
        game = ''
        if not game_code:
            params['game_error'] = "Game cannot be blank"
            valid = False
        elif game_model is None:
            params['game_error'] = ( "That's weird, we could not find any "
                                     + "records for that game" )
            valid = False
        elif game_model == self.OVER_QUOTA_ERROR:
            params['game_error'] = ( "PB Tracker is currently over its quota"
                                     + " limit for the day. Please try again "
                                     + "tomorrow." )
            valid = False
        else:
            game = game_model.game
        params[ 'game' ] = game
        params[ 'game_model' ] = game_model

        # Make sure the category doesn't already exist under a similar name
        category_code = util.get_code( category )
        category_found = False
        if not category_code:
            params['category_error'] = "Category cannot be blank"
            valid = False
        elif game_model is not None:
            infolist = json.loads( game_model.info )
            for info in infolist:
                if category_code == util.get_code( info['category'] ):
                    category_found = True
                    if category != info['category']:
                        params['category_error'] = ( "Category already exists "
                                                     + "under [" 
                                                     + info['category'] + "] "
                                                     + "(case sensitive). "
                                                     + "Hit submit again to "
                                                     + "confirm." )
                        params['category'] = info['category']
                        valid = False
                    break
        if not category_found and not games.valid_game_or_category( category ):
            params['category_error'] = ( "Category must not use any 'funny'"
                                         + " characters and can be up to 100 "
                                         + "characters long" )
            valid = False
        params[ 'category_found' ] = category_found

        # Parse the time into seconds, ensure it is valid
        ( seconds, time_error ) = util.timestr_to_seconds( time )
        if seconds is None:
            params['time_error'] = "Invalid time: " + time_error
            params['seconds'] = -1
            valid = False
        else:
            time = util.seconds_to_timestr( seconds ) # Enforce standard form
            params[ 'time' ] = time
            params[ 'seconds' ] = seconds

        # Parse the date, ensure it is valid
        ( params['date'], params['date_error'] ) = util.datestr_to_date( 
            datestr )
        if params['date_error']:
            params['date_error'] = "Invalid date: " + params['date_error']
            valid = False
                
        # Check that if this is a best known time, then it beats the old
        # best known time.
        if is_bkt and game_model is not None:
            gameinfolist = json.loads( game_model.info )
            for gameinfo in gameinfolist:
                if gameinfo['category'] == params['category']:
                    if( gameinfo.get( 'bk_seconds' ) is not None
                        and gameinfo['bk_seconds'] <= seconds ):
                        s = ( "This time does not beat current best known "
                              + "time of " + util.seconds_to_timestr( 
                                  gameinfo.get( 'bk_seconds' ) ) 
                              + " by " + gameinfo['bk_runner'] 
                              + " (if best known time is incorrect, you can "
                              + "update best known time after submission)" )
                        params['bkt_error'] = s
                        params['is_bkt'] = False
                        valid = False
                    break
                
        # Check that if this is not the best known time, then it doesn't beat
        # the old best known time
        if not is_bkt and game_model is not None:
            gameinfolist = json.loads( game_model.info )
            for gameinfo in gameinfolist:
                if gameinfo['category'] == params['category']:
                    if( gameinfo.get( 'bk_seconds' ) is not None
                        and seconds < gameinfo['bk_seconds'] ):
                        s = ( "This time beats the current best known time of "
                              + util.seconds_to_timestr( 
                                gameinfo.get( 'bk_seconds' ) )
                              + " by " + gameinfo['bk_runner']
                              + " (if best known time is incorrect, you can "
                              + "update best known time after submission)" )
                        params['bkt_error'] = s
                        params['is_bkt'] = True
                        valid = False
                    break

        # Make sure that the notes are not too long
        if len( notes ) > 140:
            params['notes_error'] = "Notes must be at most 140 characters"
            valid = False

        params['valid'] = valid
        
        if run_id:
            success = self.put_existing_run( params )
        else:
            success = self.put_new_run( params )
        if success:
            self.redirect( "/runner/" + util.get_code( user.username )
                           + "?q=view-all" )
        elif game_model is not None:
            try:
                # Grab all of the categories for autocompleting
                params['categories'] = game_model.categories( )
                params['user'] = user
                self.render( "submit.html", **params )
            except google.appengine.runtime.DeadlineExceededError:
                self.error( 403 )
                self.render( "deadline_exceeded.html", user=user )
        else:
            self.error( 404 )
            self.render( "404.html", user=user )
