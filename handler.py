import webapp2
import os
import jinja2
import util
import runners
import runs
import games
import logging

from operator import itemgetter

from google.appengine.api import memcache
from google.appengine.ext import db

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join
                                   (os.path.dirname(__file__), 
                                    'templates')), autoescape = True)

class Handler(webapp2.RequestHandler):
    # Writing and rendering utility functions
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = JINJA_ENVIRONMENT.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    # User login functions, including where to return after a login/signup
    def login(self, user_id):
        cookie = 'user_id={0};Path=/'.format(util.make_secure_val
                                             (str(user_id)))
        self.response.headers.add_header('Set-Cookie', cookie)

    def get_user( self ):
        cookie_val = self.request.cookies.get('user_id')
        if cookie_val:
            username_code = util.check_secure_val( cookie_val )
            if username_code:
                return runners.Runners.get_by_key_name( username_code, 
                                                        parent=runners.key() )

    def set_return_url(self, url):
        cookie = 'return_url=' + url + ';Path=/'
        self.response.headers.add_header('Set-Cookie', cookie)        
        
    def goto_return_url(self):
        url = self.request.cookies.get('return_url')
        if url:
            self.redirect(str(url))
        else:
            logging.warning("No return_url found; redirecting to root page")
            self.redirect("/")

    # Memcache / Datastore functions
    def get_username_memkey( self, username_code ):
        return username_code + ":username"

    def get_username( self, username_code ):
        key = self.get_username_memkey( username_code )
        username = memcache.get( key )
        if username is None:
            # Not in memcache, so check the database
            runner = runners.Runners.get_by_key_name( username_code,
                                                      parent=runners.key() )
            if runner:
                username = runner.username
                if memcache.set( key, username ):
                    logging.debug( "Set username in memcache for " 
                                   + username )
                else:
                    logging.warning( "Failed to set username for "
                                     + username + " in memcache" )
        else:
            logging.debug( "Got username for " + username 
                           + " in memcache" )
        return username

    def update_cache_username( self, username_code, username ):
        key = self.get_username_memkey( username_code )
        if memcache.set( key, username ):
            logging.debug( "Updated username for " + username 
                          + " in memcache" )
        else:
            logging.error( "Failed to update username for " + username 
                           + " in memcache" )

    def get_game_model_memkey( self, game_code ):
        return game_code + ":game_model"

    def get_game_model( self, game_code ):
        key = self.get_game_model_memkey( game_code )
        game_model = memcache.get( key )
        if game_model is None:
            # Not in memcache, so get the game from datastore
            game_model = games.Games.get_by_key_name( game_code,
                                                      parent=games.key() )
            if memcache.set( key, game_model ):
                logging.debug( "Set game_model in memcache for game_code " 
                               + game_code )
            else:
                logging.warning( "Failed to set game_model for game_code " 
                                 + game_code + " in memcache" )
        else:
            logging.debug( "Got game_model for game_code " + game_code 
                          + " from memcache" )
        return game_model

    def update_cache_game_model( self, game_code, game_model ):
        key = self.get_game_model_memkey( game_code )
        if memcache.set( key, game_model ):
            logging.debug( "Updated game_model for game_code " + game_code 
                          + " in memcache" )
        else:
            logging.error( "Failed to update game_model for game_code " 
                           + game_code + " in memcache" )

    def get_pblist_memkey( self, username ):
        return username + ":pblist"

    def get_pblist( self, username ):
        key = self.get_pblist_memkey( username )
        pblist = memcache.get( key )
        if pblist is None:
            # Not in memcache, so construct the pblist and store in memcache.
            # pblist is a list of dictionaries with 3 indices, 'game', 
            # 'game_code' and 'infolist'.  The infolist is another list of 
            # dictionaries containing all the info for each pb of the game.
            pblist = [ ]
            # Use a projection query to get all of the unique game, category
            # pairs
            q = db.Query( runs.Runs, projection=('game', 'category'), 
                          distinct=True )
            q.ancestor( runs.key() )
            q.filter( 'username =', username )
            q.order( 'game' )
            q.order( 'category' )
            q.order( '-datetime_created' )# Grab the last 1000 game,categories
            cur_game = None
            for run in q.run( limit = 1000 ):
                # For each unique game, category pair, get the fastest run
                q2 = db.Query(runs.Runs, 
                              projection=('seconds', 'video'))
                q2.ancestor( runs.key() )
                q2.filter('username =', username)
                q2.filter('game =', run.game)
                q2.filter('category =', run.category)
                q2.order('seconds')
                q2.order('datetime_created')# Break ties by getting oldest run
                pb_run = q2.get()

                # Add the fastest run to the pblist
                if run.game != cur_game:
                    # New game
                    pb = dict( game = run.game, 
                               game_code = util.get_code( run.game ),
                               infolist = [ ] )
                    pblist.append( pb )
                    cur_game = run.game

                info = dict( category = run.category, 
                             seconds = pb_run.seconds,
                             time = util.seconds_to_timestr( pb_run.seconds ),
                             video = pb_run.video )
                pb['infolist'].append( info )
            if memcache.set( key, pblist ):
                logging.debug( "Set pblist in memcache for " + username )
            else:
                logging.warning( "Failed to set new pblist for " + username
                                 + " in memcache" )
        else:
            logging.debug( "Got pblist for " + username + " from memcache" )
        return pblist

    def update_cache_pblist(self, username, pblist):
        key = self.get_pblist_memkey( username )
        if memcache.set( key, pblist ):
            logging.debug( "Updated pblist for " + username + " in memcache" )
        else:
            logging.error( "Failed to update pblist for " + username 
                           + " in memcache" )

    def get_rundict_memkey( self, game ):
        return game + ":rundict"

    def get_rundict( self, game ):
        key = self.get_rundict_memkey( game )
        rundict = memcache.get( key )
        if rundict is None:
            # Not in memcache, so construct the runs and store it in memcache
            # Rundict is a dictionary[category] of lists of dictionaries
            rundict = dict( )
            # Use a projection query to get all of the unique 
            # username, category pairs
            q = db.Query( runs.Runs, projection=('username', 'category'), 
                          distinct=True )
            q.ancestor( runs.key() )
            q.filter( 'game =', game )
            for run in q.run( limit = 1000 ):
                # For each unique username, category pair, get that users
                # fastest run for the category
                q2 = db.Query( runs.Runs, projection=('seconds', 'video') )
                q2.ancestor( runs.key() )
                q2.filter( 'game =', game )
                q2.filter( 'category =', run.category )
                q2.filter( 'username =', run.username )
                q2.order( 'seconds' )
                q2.order( 'datetime_created' )
                pb = q2.get( )
                # Append the (user, time) to the category's list
                item = dict( username = run.username,
                             username_code = util.get_code( run.username ),
                             seconds = pb.seconds,
                             time = util.seconds_to_timestr( pb.seconds ),
                             video = pb.video )
                runlist = rundict.get( run.category )
                if runlist:
                    runlist.append( item )
                else:
                    runlist = [ item ]
                rundict[ run.category ] = runlist

            # For each category, sort the runlist by seconds
            for category, runlist in rundict.iteritems():
                runlist.sort( key=itemgetter('seconds') )
                rundict[ category ] = runlist

            if memcache.set( key, rundict ):
                logging.debug( "Set rundict in memcache for " + game )
            else:
                logging.warning( "Failed to set new rundict for " + game
                                 + " in memcache" )
        else:
            logging.debug( "Got rundict for " + game + " from memcache" )
        return rundict

    def update_cache_rundict( self, game, rundict ):
        key = self.get_rundict_memkey( game )
        if memcache.set( key, rundict ):
            logging.debug( "Updated rundict for " + game + " in memcache" )
        else:
            logging.error( "Failed to update rundict for " + game 
                           + " in memcache" )

    def get_gamelist_memkey( self ):
        return "gamelist"

    def get_gamelist( self ):
        key = self.get_gamelist_memkey( )
        gamelist = memcache.get( key )
        fresh = True
        if gamelist is None:
            # Build the gamelist, which is a list of dictionaries where each
            # dict gives the game, game_code and number of pbs for that game.
            # The list is sorted by numbers of pbs for the game
            gamelist = [ ]
            q = db.Query( runs.Runs, projection=['game'], distinct=True )
            q.ancestor( runs.key() )
            for run in q.run( limit=10000 ):
                q2 = db.Query( runs.Runs, projection=('username', 'category'),
                               distinct=True )
                q2.ancestor( runs.key() )
                q2.filter( 'game =', run.game )
                num_pbs = q2.count( limit=1000 )
                gamelist.append( dict( game = run.game,
                                       game_code = util.get_code( run.game ),
                                       num_pbs = num_pbs ) )
            gamelist.sort( key=itemgetter('game_code') )
            gamelist.sort( key=itemgetter('num_pbs'), reverse=True )
            if memcache.set( key, gamelist ):
                logging.debug( "Set gamelist in memcache" )
            else:
                logging.warning( "Failed to set new gamelist in memcache" )
        else:
            fresh = False
            logging.debug( "Got gamelist from memcache" )
        return ( gamelist, fresh )

    def update_cache_gamelist( self, gamelist ):
        key = self.get_gamelist_memkey( )
        if memcache.set( key, gamelist ):
            logging.debug( "Updated gamelist in memcache" )
        else:
            logging.error( "Failed to update gamelist in memcache" )

    def get_runnerlist_memkey( self ):
        return "runnerlist"

    def get_runnerlist( self ):
        key = self.get_runnerlist_memkey( )
        fresh = True
        runnerlist = memcache.get( key )
        if runnerlist is None:
            # Build the runnerlist, which is a list of dictionaries where each
            # dict gives the username and number of pbs for that user.
            # The list is sorted by numbers of pbs for the user.
            runnerlist = [ ]
            q = db.Query( runners.Runners, projection=['username'] )
            q.ancestor( runners.key() )
            q.order( 'username' )
            for runner in q.run( limit=100000 ):
                q2 = db.Query( runs.Runs, 
                               projection=('game', 'category'),
                               distinct=True )
                q2.ancestor( runs.key() )
                q2.filter('username =', runner.username)
                num_pbs = q2.count( limit=1000 )
                runnerlist.append( 
                    dict( username = runner.username, 
                          username_code = util.get_code( runner.username ),
                          num_pbs = num_pbs ) )
            runnerlist.sort( key=itemgetter('num_pbs'), reverse=True )
            if memcache.set( key, runnerlist ):
                logging.debug( "Set runnerlist in memcache" )
            else:
                logging.warning( "Failed to set new runnerlist in memcache" )
        else:
            logging.debug( "Got runnerlist from memcache" )
            fresh = False
        return ( runnerlist, fresh )

    def update_cache_runnerlist( self, runnerlist ):
        key = self.get_runnerlist_memkey( )
        if memcache.set( key, runnerlist ):
            logging.debug( "Updated runnerlist in memcache" )
        else:
            logging.error( "Failed to update runnerlist in memcache" )

    def get_runlist_for_runner_memkey( self, username ):
        return username + ":runlist_for_runner"

    def get_runlist_for_runner( self, username ):
        key = self.get_runlist_for_runner_memkey( username )
        runlist = memcache.get( key )
        fresh = True
        if runlist is None:
            # Not in memcache, so construct the runlist and store in memcache.
            runlist = [ ]
            q = runs.Runs.all( )
            q.ancestor( runs.key() )
            q.filter( 'username =', username )
            q.order( '-datetime_created' )
            for run in q.run( limit = 1000 ):
                runlist.append( dict( run_id = str( run.key().id() ),
                                      game = run.game,
                                      game_code = util.get_code( run.game ),
                                      category = run.category,
                                      time = util.
                                      seconds_to_timestr( run.seconds ),
                                      date = run.datetime_created.strftime(
                                          "%a %b %d %H:%M:%S %Y" ),
                                      video = run.video ) )

            if memcache.set( key, runlist ):
                logging.debug( "Set runlist for runner in memcache for " 
                               + username )
            else:
                logging.warning( "Failed to set new runlist for runner " 
                                 + username + " in memcache" )
        else:
            fresh = False
            logging.debug( "Got runlist for runner " + username 
                           + " from memcache" )
        return ( runlist, fresh )

    def update_cache_runlist_for_runner( self, username, runlist ):
        key = self.get_runlist_for_runner_memkey( username )
        if memcache.set( key, runlist ):
            logging.debug( "Updated runlist for runner " + username 
                           + " in memcache" )
        else:
            logging.error( "Failed to update runlist for runner " + username 
                           + " in memcache" )
