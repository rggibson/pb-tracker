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
                       time = time, error = "Invalid time" )

        # Parse the time into seconds, ensure it is valid
        parts = time.split(':')
        if( len( parts ) > 3 ):
            self.render("submit.html", **params)
            return
        try:
            seconds = int( parts[ -1 ] )
        except ValueError:
            self.render("submit.html", **params)
            return
        if( seconds < 0 or seconds >= 60 ):
            params['error'] = "Invalid time: seconds out of range"
            self.render("submit.html", **params)
            return
        if( len( parts ) > 1 ):
            try:
                minutes = int( parts[ -2 ] )
            except ValueError:
                self.render("submit.html", **params)
                return
            if( minutes < 0 or minutes >= 60 ):
                params['error'] = "Invalid time: minutes out of range"
                self.render("submit.html", **params)
                return
            seconds += 60 * minutes;
            if( len( parts ) > 2 ):
                try:
                    hours = int( parts[ 0 ] )
                except ValueError:
                    self.render("submit.html", **params)
                    return
                if( hours < 0 ):
                    params['error'] = "Invalid time: hours out of range"
                    self.render("submit.html", **params)
                    return
                seconds += 3600 * hours

        # Add a new run to the database
        run = runs.Runs( username = user.username,
                         game = game,
                         category = category,
                         time = seconds,
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
                    pblist[ i ][ 'seconds' ] = seconds
                    pblist[ i ][ 'time' ] = util.seconds_to_timestr( seconds )
                    self.update_cache_pblist( user.username, pblist )
                break
        if not found_time:
            pblist.append( dict( game = game, category = category,
                                 seconds = seconds, 
                                 time = util.seconds_to_timestr( seconds ) ) )
            # Hopefully this sorts by game, then breaks ties by category
            # (both sorts are done alphabetically, of course)
            sorted_pblist = sorted( pblist, key=lambda k: 
                                    ( k['game'], k['category'] ) )
            self.update_cache_pblist( user.username, sorted_pblist )
                                                    
        self.redirect( "/runner/" + user.username )
