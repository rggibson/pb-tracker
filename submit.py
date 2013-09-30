import handler
import runners
import util
import logging
import runs
import games

from operator import itemgetter

from google.appengine.ext import db

class Submit( handler.Handler ):
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
            run = runs.Runs.get_by_id( long( run_id ), parent=runs.key() )
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
            for c in game_model.categories:
                if category_code == util.get_code( c ):
                    category_found = True
                    if category != c:
                        params['category_error'] = ( "Category already exists "
                                                     + "under [" + c + "] "
                                                     + "(case sensitive). "
                                                     + "Hit submit again to "
                                                     + "confirm." )
                        params['category'] = c
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
        self.update_pblist( params )
        self.update_rundict( params )
        self.update_runlist_for_runner( params )
                     
        # Check whether this is the first run for this username, game,
        # category combination.  This will determine whether we need to check
        # for gamelist and runnerlist updates.
        num_runs = self.num_runs( user.username, game, category, 2 )
        if num_runs <= 0:
            logging.error( "Unexpected count [" + str(count) 
                           + "] for number of runs for "
                           + username + ", " + game + ", " + category )
        if num_runs == 1:
            self.update_gamelist( params )
            self.update_runnerlist( params )


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
        new_run = runs.Runs.get_by_id( long( run_id ), parent=runs.key() )
        if not new_run or new_run.username != user.username:
            self.error( 404 )
            self.render( "404.html" )
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

        # Replace the old run in the pblist, if necessary
        pblist = self.get_pblist( user.username )
        for i, pb in enumerate( pblist ):
            found_game = False
            if( pb['game'] == old_run['game'] ):
                for j, info in enumerate( pb['infolist'] ):
                    if( info['category'] == old_run['category'] ):
                        if( info['seconds'] == old_run['seconds'] ):
                            # Yes we do need to replace it
                            q = db.Query( runs.Runs, 
                                          projection=('seconds', 'video') )
                            q.ancestor( runs.key() )
                            q.filter( 'username =', user.username )
                            q.filter( 'game =', old_run[ 'game' ] )
                            q.filter( 'category =', old_run[ 'category' ] )
                            q.order( 'seconds' )
                            q.order( 'datetime_created' )
                            pb_run = q.get( )
                            if pb_run:
                                info[ 'seconds' ] = pb_run.seconds
                                info[ 'video' ] = pb_run.video
                            else:
                                # No other runs for game, category combo
                                del pb[ 'infolist' ][ j ]
                                if len( pb[ 'infolist' ] ) <= 0:
                                    del pblist[ i ]
                            self.update_cache_pblist( user.username, pblist )
                        break 
                break

        # Replace the old run in the rundict, if necessary
        rundict = self.get_rundict( old_run[ 'game' ] )
        runlist = rundict.get( old_run[ 'category' ] )
        if not runlist:
            runlist = [ ]
        for i, run in enumerate( runlist ):
            if( run[ 'username' ] == user.username ):
                if( run[ 'seconds' ] == old_run[ 'seconds' ] ):
                    # Yes, we need replace 
                    q = db.Query( runs.Runs, projection=('seconds', 'video') )
                    q.ancestor( runs.key() )
                    q.filter( 'game =', old_run[ 'game' ] )
                    q.filter( 'category =', old_run[ 'category' ] )
                    q.filter( 'username =', user.username )
                    q.order( 'seconds' )
                    q.order( 'datetime_created' )
                    pb_run = q.get( )
                    if pb_run:
                        run[ 'seconds' ] = pb_run.seconds
                        run[ 'video' ] = pb_run.video
                    else:
                        # No other run for game, category combo
                        del runlist[ i ]
                        if len( runlist ) <= 0:
                            del rundict[ old_run[ 'category' ] ]
                    if runlist:
                        runlist.sort( key=itemgetter('seconds') )
                    self.update_cache_rundict( old_run[ 'game' ], rundict )
                break

        num_runs = self.num_runs( user.username, old_run[ 'game' ], 
                                  old_run[ 'category' ], 1 )
        if num_runs <= 0:
            # Fix the gamelist with the removal of the old run
            ( gamelist, fresh ) = self.get_gamelist( )
            if not fresh:
                for i, gamedict in enumerate( gamelist ):
                    if( gamedict[ 'game' ] == old_run[ 'game' ] ):
                        gamedict['num_pbs'] -= 1
                        if gamedict['num_pbs'] <= 0:
                            del gamelist[ i ]
                        gamelist.sort( key=itemgetter('game_code') )
                        gamelist.sort( key=itemgetter('num_pbs'), 
                                       reverse=True )
                        self.update_cache_gamelist( gamelist )
                        break
            # Fix the runnerlist with the removal of the old run
            ( runnerlist, fresh ) = self.get_runnerlist( )
            if not fresh:
                for runnerdict in runnerlist:
                    if( runnerdict['username'] == user.username ):
                        runnerdict['num_pbs'] -= 1
                        runnerlist.sort( key=itemgetter('username') )
                        runnerlist.sort( key=itemgetter('num_pbs'), 
                                         reverse=True )
                        self.update_cache_runnerlist( runnerlist )
                        break

        # Replace the old run in the runlist for runner
        ( runlist, fresh ) = self.get_runlist_for_runner( user.username )
        if not fresh:
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

        # Update games
        self.update_games( params )

        # Update memcache
        self.update_pblist( params )
        self.update_rundict( params )
        num_runs = self.num_runs( user.username, game, category, 2 )
        if num_runs <= 0:
            logging.error( "Unexpected count [" + str(count) 
                           + "] for number of runs for "
                           + username + ", " + game + ", " + category )
        if num_runs == 1:
            self.update_gamelist( params )
            self.update_runnerlist( params )

    def update_games( self, params ):
        game_model = params[ 'game_model' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        game_code = params[ 'game_code' ]
        category_found = params[ 'category_found' ]

        if not game_model:
            # Add a new game to the database
            game_model = games.Games( game = game,
                                      categories = [ category ],
                                      parent = games.key(),
                                      key_name = game_code )
            game_model.put( )
            logging.warning( "Put new game " + game + " with "
                             + " category " + category + " in database." )
            self.update_cache_game_model( game_code, game_model )
        elif not category_found:
            # Add a new category for this game in the database
            game_model.categories.append( category )
            game_model.put( )
            logging.debug( "Added category " + category + " to game " 
                           + game + " in database." )

    def update_pblist( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        game_code = params[ 'game_code' ]

        # Update pblist in memcache, if necessary
        pblist = self.get_pblist( user.username )
        found_time = False
        for pb in pblist:
            if( pb['game'] == game ):
                for info in pb['infolist']:
                    if( info['category'] == category ):
                        found_time = True
                        if( info['seconds'] > seconds ):
                            # Yes we do need to update
                            info[ 'seconds' ] = seconds
                            info[ 'time' ] = time
                            info[ 'video' ] = video
                            self.update_cache_pblist( user.username, pblist )
                        break
                if not found_time:
                    # User has run this game, but not this cateogry.
                    # Add the run to the pblist and update memcache.
                    info = dict( category = category,
                                 seconds = seconds,
                                 time = time,
                                 video = video )
                    pb['infolist'].append( info )
                    pb['infolist'].sort( key=itemgetter('category') )
                    self.update_cache_pblist( user.username, pblist )
                    found_time = True
                break
        if not found_time:
            # No run for this username, game combination.
            # So, add the run to this username's pblist and update memcache
            pblist.append( dict( game = game, 
                                 game_code = game_code,
                                 infolist = [ dict( category = category,
                                                    seconds = seconds, 
                                                    time = time,
                                                    video = video ) ] 
                                 ) )
            pblist.sort( key=itemgetter('game') )
            self.update_cache_pblist( user.username, pblist )

    def update_rundict( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]

        # Update rundict in memcache, if necessary
        rundict = self.get_rundict( game )
        found_runner = False
        runlist = rundict.get( category )
        if runlist:
            for run in runlist:
                if( run[ 'username' ] == user.username ):
                    found_runner = True
                    if( run[ 'seconds' ] > seconds ):
                        # Yes, we need to update
                        run[ 'seconds' ] = seconds
                        run[ 'time' ] = time
                        run[ 'video' ] = video
                        runlist.sort( key=itemgetter('seconds') )
                        self.update_cache_rundict( game, rundict )
                    break
        if not found_runner:
            # No run for this username, game, category combination.
            # So, add the run to this game's rundict and update memcache
            item = dict( username = user.username,
                         username_code = util.get_code( user.username ),
                         seconds = seconds,
                         time = time,
                         video = video )
            if runlist:
                runlist.append( item )
            else:
                runlist = [ item ]
            runlist.sort( key=itemgetter('seconds') )
            rundict[ category ] = runlist
            self.update_cache_rundict( game, rundict )            

    def num_runs( self, username, game, category, limit ):
        q = db.Query( runs.Runs, keys_only=True )
        q.ancestor( runs.key() )
        q.filter( 'username =', username )
        q.filter( 'game =', game )
        q.filter( 'category =', category )
        return q.count( limit=limit )

    def update_gamelist( self, params ):
        game_code = params[ 'game_code' ]
        game = params[ 'game' ]

        # Update gamelist in memcache if necessary
        ( gamelist, fresh ) = self.get_gamelist( )
        if not fresh:
            found_game = False
            for gamedict in gamelist:
                if( gamedict['game_code'] == game_code ):
                    found_game = True
                    # We may have a stale number for pbs, so recount
                    q = db.Query( runs.Runs, 
                                  projection=('username', 'category'),
                                  distinct=True )
                    q.ancestor( runs.key() )
                    q.filter( 'game =', game )
                    num_pbs = q.count( limit=1000 )
                    gamedict['num_pbs'] = num_pbs
                    gamelist.sort( key=itemgetter('game_code') )
                    gamelist.sort( key=itemgetter('num_pbs'), 
                                   reverse=True )
                    self.update_cache_gamelist( gamelist )
                    break
            if not found_game:
                # This game wasn't found in the gamelist, so add it
                gamelist.append( dict( game = game, game_code = game_code,
                                       num_pbs = 1 ) )
                gamelist.sort( key=itemgetter('game_code') )
                gamelist.sort( key=itemgetter('num_pbs'), reverse=True )
                self.update_cache_gamelist( gamelist )

    def update_runnerlist( self, params ):
        user = params[ 'user' ]

        # Update runnerlist in memcache if necessary
        ( runnerlist, fresh ) = self.get_runnerlist( )
        if not fresh:
            found_runner = False
            for runnerdict in runnerlist:
                if( runnerdict['username'] == user.username ):
                    found_runner = True
                    # Memcache could be stale, so recalculate num_pbs
                    q = db.Query( runs.Runs, 
                                  projection=('game', 'category'),
                                  distinct = True )
                    q.ancestor( runs.key() )
                    q.filter( 'username =', user.username )
                    num_pbs = q.count( limit=1000 )
                    runnerdict['num_pbs'] = num_pbs
                    runnerlist.sort( key=itemgetter('username') )
                    runnerlist.sort( key=itemgetter('num_pbs'), 
                                     reverse=True )
                    self.update_cache_runnerlist( runnerlist )
                    break
            if not found_runner:
                logging.error( "Failed to find " + user.username 
                               + " in runnerlist" )

    def update_runlist_for_runner( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        game_code = params[ 'game_code' ]
        category = params[ 'category' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        datetime_created = params[ 'datetime_created' ]
        run_id = params[ 'run_id' ]

        # Update runlist for runner in memcache
        ( runlist, fresh ) = self.get_runlist_for_runner( user.username )
        if not fresh:
            runlist.insert( 0, dict( run_id = run_id,
                                     game = game, game_code = game_code,
                                     category = category, time = time, 
                                     date = datetime_created.strftime(
                                         "%a %b %d %H:%M:%S %Y" ),
                                     video = video ) )
            self.update_cache_runlist_for_runner( user.username, runlist )
