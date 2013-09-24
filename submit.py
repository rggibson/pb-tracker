import handler
import runners
import util
import logging
import runs

from operator import itemgetter

from google.appengine.ext import db

class Submit(handler.Handler):
    def get(self):
        user = self.get_user()

        # TODO: Figure out how to autocomplete game, category inputs using
        # <input class="ui-autocomplete-input"> or something similar

        if not user:
            self.redirect("/")
        else:
            self.render("submit.html", user=user)

    def post(self):
        user = self.get_user()
        if not user:
            self.redirect("/")
            return

        game = self.request.get('game')
        category = self.request.get('category')
        time = self.request.get('time')
        video = self.request.get('video')

        params = dict( user = user, game = game, category = category, 
                       time = time, video = video )

        # Make sure the game doesn't already exist under a similar name
        game_code = util.get_game_or_category_code( game )
        q = runs.Runs.all()
        q.filter('game_code =', game_code)
        run = q.get()
        if run and game != run.game:
            params['game_error'] = "Game already exists under " + run.game
            params['game_error'] += " (case sensitive)." 
            params['game_error'] += "  Hit submit again to confirm."
            params['game'] = run.game
            self.render("submit.html", **params)
            return

        # Make sure the category doesn't already exist under a similar name
        category_code = util.get_game_or_category_code( category )
        q = runs.Runs.all()
        q.filter('game_code =', game_code)
        q.filter('category_code =', category_code)
        run = q.get()
        if( run and category != run.category ):
            params['category_error'] = "Category already exists under " 
            params['category_error'] += run.category + " (case sensitive)." 
            params['category_error'] += "  Hit submit again to confirm."
            params['category'] = run.category
            self.render("submit.html", **params)
            return

        # Parse the time into seconds, ensure it is valid
        (seconds, time_error) = util.timestr_to_seconds( time )
        if not seconds:
            params['time_error'] = "Invalid time: " + time_error
            self.render("submit.html", **params)
            return
        time = util.seconds_to_timestr( seconds ) # Enforce standard format

        # Add a new run to the database
        run = runs.Runs( username = user.username,
                         game = game,
                         game_code = game_code,
                         category = category,
                         category_code = category_code,
                         seconds = seconds,
                         parent = runs.key() )
        if video:
            try:
                run.video = video
            except db.BadValueError:
                params['video_error'] = "Invalid video URL"
                self.render("submit.html", **params)
                return                
        run.put()
        logging.info("Put new run for runner " + user.username
                     + ", game = " + game + ", category = " + category 
                     + ", time = " + time)

        # Update pblist in memcache, if necessary
        pblist = self.get_pblist( user.username )
        found_time = False
        for i in range( len(pblist) ):
            pb = pblist[ i ]
            if( pb['game'] == game and pb['category'] == category ):
                found_time = True
                if( pb['seconds'] > seconds ):
                    # Yes we do need to update
                    pblist[ i ][ 'seconds' ] = seconds
                    pblist[ i ][ 'time' ] = time
                    pblist[ i ][ 'video' ] = video
                    self.update_cache_pblist( user.username, pblist )
                break
        if not found_time:
            # No run for this username, game, category combination.
            # So, add the run to this username's pblist and update memcache
            pblist.append( dict( game = game, 
                                 game_code = game_code,
                                 category = category,
                                 seconds = seconds, 
                                 time = time,
                                 video = video ) )
            pblist.sort( key=itemgetter('game','category') )
            self.update_cache_pblist( user.username, pblist )
                     
        # Update rundict in memcache, if necessary
        rundict = self.get_rundict( game_code )
        found_runner = False
        runlist = rundict.get( category )
        if runlist:
            for i in range( len( rundict[ category ] ) ):
                run = rundict[ category ][ i ]
                if( run[ 'username' ] == user.username ):
                    found_runner = True
                    if( run[ 'seconds' ] > seconds ):
                        # Yes, we need to update
                        rundict[ category ][ i ][ 'seconds' ] = seconds
                        rundict[ category ][ i ][ 'time' ] = time
                        rundict[ category ][ i ][ 'video' ] = video
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
        q = db.Query( runs.Runs, projection=[] )
        q.ancestor( runs.key() )
        q.filter('username =', user.username)
        q.filter('game =', game)
        q.filter('category =', category)
        count = q.count( limit=2 )
        if( count == 1 ):
            new_combo = True
        elif( count == 2 ):
            new_combo = False
        else:
            logging.error("Unexpected count [" + str(count) 
                          + "] for number of runs for "
                          + user.username + ", " + game + ", " + category)
            new_combo = False

        if new_combo:
            # Update gamelist in memcache if necessary
            gamelist = self.get_gamelist( )
            found_game = False
            for gamedict in gamelist:
                if( gamedict['game'] == game ):
                    found_game = True
                    # We may have a stale number for pbs, so recount
                    q = db.Query( runs.Runs, 
                                  projection=('username', 'category'),
                                  distinct=True )
                    q.ancestor( runs.key() )
                    q.filter( 'game =', game )
                    num_pbs = q.count( limit=1000 )
                    gamedict['num_pbs'] = num_pbs
                    gamelist.sort( key=itemgetter('game') )
                    gamelist.sort( key=itemgetter('num_pbs'), reverse=True )
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
            runnerlist = self.get_runnerlist( )
            found_runner = False
            for runnerdict in runnerlist:
                if( runnerdict['username'] == user.username ):
                    found_runner = True
                    # Memcache could be stale, so recalculate num_pbs
                    q = db.Query( runs.Runs, projection=('game', 'category'),
                                  distinct = True )
                    q.ancestor( runs.key() )
                    q.filter( 'username =', user.username )
                    num_pbs = q.count( limit=1000 )
                    runnerdict['num_pbs'] = num_pbs
                    runnerlist.sort( key=itemgetter('username') )
                    runnerlist.sort( key=itemgetter('num_pbs'), reverse=True )
                    self.update_cache_runnerlist( runnerlist )
                    break
            if not found_runner:
                logging.error("Failed to find " + user.username 
                              + " in runnerlist")

        # All done with submission
        self.redirect( "/runner/" + user.username )
