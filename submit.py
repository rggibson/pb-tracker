import handler
import runners
import util
import logging
import runs

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

        params = dict( user = user, game = game, category = category, 
                       time = time )

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
                         parent = runs.key())
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
                    self.update_cache_pblist( user.username, pblist )
                break
        if not found_time:
            # No run for this username, game, category combination.
            # So, add the run to this username's pblist and update memcache
            pblist.append( dict( game = game, 
                                 game_code = game_code,
                                 category = category,
                                 seconds = seconds, 
                                 time = time ) )
            # Hopefully this sorts by game, then breaks ties by category
            # (both sorts are done alphabetically, of course)
            sorted_pblist = sorted( pblist, key=lambda k: 
                                    ( k['game'], k['category'] ) )
            self.update_cache_pblist( user.username, sorted_pblist )
                     
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
                        sorted_runlist = (
                            sorted( rundict[ category ],
                                    key=lambda k: k['seconds'] ) )
                        rundict[ category ] = sorted_runlist
                        self.update_cache_rundict( game_code, rundict )
                    break
        if not found_runner:
            # No run for this username, game, category combination.
            # So, add the run to this game's rundict and update memcache
            item = dict( username = user.username,
                         seconds = seconds,
                         time = time )
            if runlist:
                runlist.append( item )
            else:
                runlist = [ item ]
            sorted_runlist = sorted( runlist, key=lambda k: k['seconds'] )
            rundict[ category ] = sorted_runlist
            self.update_cache_rundict( game_code, rundict )            
                               
        self.redirect( "/runner/" + user.username )
