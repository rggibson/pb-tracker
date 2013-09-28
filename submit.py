import handler
import runners
import util
import logging
import runs
import games

from operator import itemgetter

from google.appengine.ext import db

class Submit(handler.Handler):
    def get( self ):
        user = self.get_user( )

        if not user:
            self.redirect( "/" )
        else:
            self.render( "submit.html", user=user )

    def post( self ):
        user = self.get_user( )
        if not user:
            self.redirect( "/" )
            return

        game = self.request.get('game')
        category = self.request.get('category')
        time = self.request.get('time')
        video = self.request.get('video')

        params = dict( user = user, game = game, category = category, 
                       time = time, video = video )

        # Make sure the game doesn't already exist under a similar name
        game_code = util.get_code( game )
        game_model = self.get_game_model( game_code )
        if game_model and game != game_model.game:
            params['game_error'] = ( "Game already exists under [" 
                                     + game_model.game + "] (case sensitive). "
                                     + "Hit submit again to confirm." )
            params['game'] = game_model.game
            self.render("submit.html", **params)
            return

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

        # Parse the time into seconds, ensure it is valid
        ( seconds, time_error ) = util.timestr_to_seconds( time )
        if not seconds:
            params['time_error'] = "Invalid time: " + time_error
            self.render( "submit.html", **params )
            return
        time = util.seconds_to_timestr( seconds ) # Enforce standard format

        if not game_model:
            # Add a new game to the database
            game_model = games.Games( game = game,
                                      categories = [ category ],
                                      parent = games.key(),
                                      key_name = game_code )
            game_model.put( )
            logging.warning( "Put new game " + game_model.game + " with "
                             + " category " + category + " in database." )
            self.update_cache_game_model( game_code, game_model )
        elif not category_found:
            # Add a new category for this game in the database
            game_model.categories.append( category )
            game_model.put( )
            logging.info( "Added category " + category + " to game " 
                          + game_model.game + " in database." )

        # Add a new run to the database
        new_run = runs.Runs( username = user.username,
                             game_code = game_code,
                             category = category,
                             seconds = seconds,
                             parent = runs.key() )
        if video:
            try:
                new_run.video = video
            except db.BadValueError:
                params['video_error'] = "Invalid video URL"
                self.render( "submit.html", **params )
                return                
        new_run.put( )
        logging.debug( "Put new run for runner " + user.username
                       + ", game = " + game + ", category = " + category 
                       + ", time = " + time)

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
                     
        # Update rundict in memcache, if necessary
        rundict = self.get_rundict( game_code )
        found_runner = False
        runlist = rundict.get( category )
        if runlist:
            for run in rundict[ category ]:
                if( run[ 'username' ] == user.username ):
                    found_runner = True
                    if( run[ 'seconds' ] > seconds ):
                        # Yes, we need to update
                        run[ 'seconds' ] = seconds
                        run[ 'time' ] = time
                        run[ 'video' ] = video
                        rundict[ category ].sort( key=itemgetter('seconds') )
                        self.update_cache_rundict( game_code, rundict )
                    break
        if not found_runner:
            # No run for this username, game, category combination.
            # So, add the run to this game's rundict and update memcache
            item = dict( username = user.username,
                         seconds = seconds,
                         time = time,
                         video = video )
            if runlist:
                runlist.append( item )
            else:
                runlist = [ item ]
            runlist.sort( key=itemgetter('seconds') )
            rundict[ category ] = runlist
            self.update_cache_rundict( game_code, rundict )            

        # Check whether this is the first run for this username, game,
        # category combination.  This will determine whether we need to check
        # for gamelist and runnerlist updates.
        q = db.Query( runs.Runs, keys_only=True )
        q.ancestor( runs.key() )
        q.filter( 'username =', user.username )
        q.filter( 'game_code =', game_code )
        q.filter( 'category =', category )
        count = q.count( limit=2 )
        if( count == 1 ):
            new_combo = True
        elif( count == 2 ):
            new_combo = False
        else:
            logging.error( "Unexpected count [" + str(count) 
                           + "] for number of runs for "
                           + user.username + ", " + game + ", " + category )
            new_combo = False

        if new_combo:
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
                        q.filter( 'game_code =', game_code )
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
                    gamelist.sort( key=itemgetter('game') )
                    gamelist.sort( key=itemgetter('num_pbs'), reverse=True )
                    self.update_cache_gamelist( gamelist )

            # Update runnerlist in memcache if necessary
            ( runnerlist, fresh ) = self.get_runnerlist( )
            if not fresh:
                found_runner = False
                for runnerdict in runnerlist:
                    if( runnerdict['username'] == user.username ):
                        found_runner = True
                        # Memcache could be stale, so recalculate num_pbs
                        q = db.Query( runs.Runs, 
                                      projection=('game_code', 'category'),
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

        # Update runlist for runner in memcache
        ( runlist, fresh ) = self.get_runlist_for_runner( user.username )
        if not fresh:
            runlist.append( dict( game = game, game_code = game_code,
                                  category = category, time = time, 
                                  date = new_run.datetime_created.strftime(
                                      "%a %b %d %H:%M:%S %Y" ),
                                  video = video ) )
            self.update_cache_runlist_for_runner( user.username, runlist )

        # All done with submission
        self.redirect( "/runner/" + util.get_code( user.username ) )
