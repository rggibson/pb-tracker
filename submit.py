import runhandler
import util
import logging
import runs
import json

from google.appengine.ext import db

class Submit( runhandler.RunHandler ):
    def get( self ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        params = dict( user=user )

        # Are we editing an existing run?
        run_id = self.request.get( 'edit' )
        if run_id:
            # Grab the run to edit
            run = self.get_run_by_id( run_id )
            if not run or user.username != run.username:
                self.error( 404 )
                self.render( "404.html", user=user )
                return
            params[ 'game' ] = run.game
            params[ 'category' ] = run.category
            params[ 'time' ] = util.seconds_to_timestr( run.seconds )
            params[ 'run_id' ] = run_id
            if run.video:
                params[ 'video' ] = run.video
            
        self.render( "submit.html", **params )

    def post( self ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        game = self.request.get( 'game' )
        category = self.request.get( 'category' )
        time = self.request.get( 'time' )
        video = self.request.get( 'video' )
        run_id = self.request.get( 'edit' )

        params = dict( user = user, game = game, category = category, 
                       time = time, video = video, run_id = run_id )

        # Make sure the game doesn't already exist under a similar name
        game_code = util.get_code( game )
        game_model = self.get_game_model( game_code )
        if game_model and game != game_model.game:
            params['game_error'] = ( "Game already exists under [" 
                                     + game_model.game + "] (case sensitive). "
                                     + "Hit submit again to confirm." )
            params['game'] = game_model.game
            self.render( "submit.html", **params )
            return
        params[ 'game_code' ] = game_code
        params[ 'game_model' ] = game_model

        # Make sure the category doesn't already exist under a similar name
        category_code = util.get_code( category )
        category_found = False
        if game_model:
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
                        self.render( "submit.html", **params )
                        return
                    break
        params[ 'category_found' ] = category_found

        # Parse the time into seconds, ensure it is valid
        ( seconds, time_error ) = util.timestr_to_seconds( time )
        if not seconds:
            params['time_error'] = "Invalid time: " + time_error
            self.render( "submit.html", **params )
            return
        time = util.seconds_to_timestr( seconds ) # Enforce standard format
        params[ 'time' ] = time
        params[ 'seconds' ] = seconds

        if run_id:
            self.put_existing_run( params )
            self.redirect( "/runner/" + util.get_code( user.username )
                           + "?q=view-all" )
        else:
            self.put_new_run( params )
            self.redirect( "/runner/" + util.get_code( user.username ) )


    def put_new_run( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]

        # Add a new run to the database
        new_run = runs.Runs( username = user.username,
                             game = game,
                             category = category,
                             seconds = seconds,
                             parent = runs.key() )
        if video:
            try:
                new_run.video = video
            except db.BadValueError:
                params[ 'video_error' ] = "Invalid video URL"
                self.render( "submit.html", **params )
                return                
        new_run.put( )
        params[ 'run_id' ] = str( new_run.key().id() )
        params[ 'datetime_created' ] = new_run.datetime_created
        logging.debug( "Put new run for runner " + user.username
                       + ", game = " + game + ", category = " + category 
                       + ", time = " + time )

        # Update games.Games
        self.update_games( params )

        # Update memcache
        self.update_cache_run_by_id( new_run.key().id(), new_run )
        # Must update runinfo before updating pblist, gamepage since these 
        # both rely on runinfo being up to date
        self.update_runinfo_put( params )
        self.update_pblist_put( params )
        self.update_gamepage_put( params )
        self.update_runlist_for_runner_put( params )
                     
        # Check whether this is the first run for this username, game,
        # category combination.  This will determine whether we need to check
        # for gamelist and runnerlist updates.
        num_runs = self.num_runs( user.username, game, category, 2 )
        if num_runs <= 0:
            logging.error( "Unexpected count [" + str(count) 
                           + "] for number of runs for "
                           + username + ", " + game + ", " + category )
        if num_runs == 1:
            self.update_gamelist_put( params )
            self.update_runnerlist_put( params )


    def put_existing_run( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        game_code = params[ 'game_code' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        run_id = params[ 'run_id' ]

        # Grab the old run, which we will update to be the new run
        new_run = self.get_run_by_id( run_id )
        if not new_run or new_run.username != user.username:
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        # Store the contents of the old run
        old_run = dict( game = new_run.game,
                        category = new_run.category,
                        seconds = new_run.seconds )

        # Update the run
        new_run.game = game
        new_run.category = category
        new_run.seconds = seconds
        if video:
            try:
                new_run.video = video
            except db.BadValueError:
                params['video_error'] = "Invalid video URL"
                self.render( "submit.html", **params )
                return
        elif new_run.video:
            new_run.video = None
        new_run.put( )
        logging.debug( "Put updated run for runner " + user.username
                       + ", game = " + game + ", category = " + category
                       + ", time= " + time + ", run_id = " + run_id )
        params[ 'datetime_created' ] = new_run.datetime_created

        # Update games
        self.update_games( params )

        # Update memcache with the removal of the old run and addition of the
        # new run.
        self.update_cache_run_by_id( run_id, new_run )
        # Must update runinfo before pblist and gamepage as in put_new_run()
        self.update_runinfo_delete( user, old_run )
        self.update_runinfo_put( params )
        self.update_pblist_delete( user, old_run )
        self.update_pblist_put( params )
        self.update_gamepage_delete( user, old_run )
        self.update_gamepage_put( params )

        # Update gamelist and runnerlist in memcache
        num_runs = self.num_runs( user.username, old_run[ 'game' ], 
                                  old_run[ 'category' ], 1 )
        if num_runs <= 0:
            self.update_gamelist_delete( old_run )
            self.update_runnerlist_delete( user )
        num_runs = self.num_runs( user.username, game, category, 2 )
        if num_runs <= 0:
            logging.error( "Unexpected count [" + str(count) 
                           + "] for number of runs for "
                           + username + ", " + game + ", " + category )
            self.update_cache_gamelist( None )
            self.update_cache_runnerlist( None )
        elif num_runs == 1:
            self.update_gamelist_put( params )
            self.update_runnerlist_put( params )

        # Replace the old run in the runlist for runner in memcache
        runlist = self.get_runlist_for_runner( user.username, no_refresh=True )
        if runlist:
            for run in runlist:
                if run[ 'run_id' ] == run_id:
                    run[ 'game' ] = game
                    run[ 'game_code' ] = game_code
                    run[ 'category' ] = category
                    run[ 'time' ] = time
                    run[ 'video' ] = video
                    self.update_cache_runlist_for_runner( user.username, 
                                                          runlist )
                    break
