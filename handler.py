import webapp2
import os
import jinja2
import util
import runners
import runs
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

    def get_user(self):
        cookie_val = self.request.cookies.get('user_id')
        if cookie_val:
            user_id = util.check_secure_val(cookie_val)
            if user_id:
                return runners.Runners.get_by_id(long(user_id), 
                                                 parent=runners.key())

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
    def get_pblist_memkey( self, username ):
        return username + ":pblist"

    def get_pblist(self, username):
        key = self.get_pblist_memkey( username )
        pblist = memcache.get( key )
        if pblist is None:
            # Not in memcache, so construct the pblist and store it in memcache
            pblist = [ ]
            # Use a projection query to get all of the unique game, category
            # pairs
            q = db.Query(runs.Runs, projection=('game', 'category'), 
                         distinct=True)
            q.ancestor(runs.key())
            q.filter('username =', username)
            # Hopefully this sorts by game first, breaking ties by category
            q.order('game')
            q.order('category')
            q.order('-datetime_created')
            for run in q.run( limit = 1000 ):
                # For each unique game, category pair, get the fastest run
                q2 = db.Query(runs.Runs, projection=('game_code', 'seconds'))
                q2.ancestor(runs.key())
                q2.filter('username =', username)
                q2.filter('game =', run.game)
                q2.filter('category =', run.category)
                q2.order('seconds')
                pb = q2.get()
                pblist.append( 
                    dict( game = run.game, game_code = pb.game_code,
                          category = run.category, seconds = pb.seconds,
                          time = util.seconds_to_timestr( pb.seconds ) ) )
            if memcache.set( key, pblist ):
                logging.info("Set pblist in memcache for " + username)
            else:
                logging.warning("Failed to set new pblist for " + username
                                + " in memcache")
        else:
            logging.info("Got pblist for " + username + " from memcache")
        return pblist

    def update_cache_pblist(self, username, pblist):
        key = self.get_pblist_memkey( username )
        if memcache.set( key, pblist ):
            logging.info("Updated pblist for " + username + " in memcache")
        else:
            logging.error("Failed to update pblist for " + username 
                          + " in memcache")

    def get_rundict_memkey( self, game_code ):
        return game_code + ":rundict"

    def get_rundict(self, game_code):
        key = self.get_rundict_memkey( game_code )
        rundict = memcache.get( key )
        if rundict is None:
            # Not in memcache, so construct the runs and store it in memcache
            # Rundict is a dictionary[category] of lists of dictionaries
            rundict = dict( )
            # Use a projection query to get all of the unique 
            # username, category pairs
            q = db.Query(runs.Runs, projection=('username', 'category'), 
                         distinct=True)
            q.ancestor(runs.key())
            q.filter('game_code =', game_code)
            for run in q.run( limit = 1000 ):
                # For each unique username, category pair, get that users
                # fastest run for the category
                q2 = db.Query(runs.Runs, projection=['seconds'])
                q2.ancestor(runs.key())
                q2.filter('game_code =', game_code)
                q2.filter('category =', run.category)
                q2.filter('username =', run.username)
                q2.order('seconds')
                pb = q2.get()
                # Append the (user, time) to the category's list
                item = dict( username = run.username,
                             seconds = pb.seconds,
                             time = util.seconds_to_timestr( pb.seconds ) )
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
                logging.info("Set rundict in memcache for " + game_code)
            else:
                logging.warning("Failed to set new rundict for " + game_code
                                + " in memcache")
        else:
            logging.info("Got rundict for " + game_code + " from memcache")
        return rundict

    def update_cache_rundict(self, game_code, rundict):
        key = self.get_rundict_memkey( game_code )
        if memcache.set( key, rundict ):
            logging.info("Updated rundict for " + game_code + " in memcache")
        else:
            logging.error("Failed to update rundict for " + game_code 
                          + " in memcache")

    def get_gamelist_memkey( self ):
        return "gamelist"

    def get_gamelist( self ):
        key = self.get_gamelist_memkey( )
        gamelist = memcache.get( key )
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
                q2.filter('game =', run.game)
                num_pbs = q2.count( limit=1000 )
                gamelist.append( 
                    dict( 
                        game = run.game,
                        game_code = util.get_game_or_category_code( run.game ),
                        num_pbs = num_pbs ) )
            gamelist.sort( key=itemgetter('game') )
            gamelist.sort( key=itemgetter('num_pbs'), reverse=True )
            if memcache.set( key, gamelist ):
                logging.info("Set gamelist in memcache")
            else:
                logging.warning("Failed to set new gamelist in memcache")
        else:
            logging.info("Got gamelist from memcache")
        return gamelist

    def update_cache_gamelist(self, gamelist):
        key = self.get_gamelist_memkey( )
        if memcache.set( key, gamelist ):
            logging.info("Updated gamelist in memcache")
        else:
            logging.error("Failed to update gamelist in memcache")

    def get_runnerlist_memkey( self ):
        return "runnerlist"

    def get_runnerlist( self ):
        key = self.get_runnerlist_memkey( )
        runnerlist = memcache.get( key )
        if runnerlist is None:
            # Build the runnerlist, which is a list of dictionaries where each
            # dict gives the username and number of pbs for that user.
            # The list is sorted by numbers of pbs for the user.
            runnerlist = [ ]
            q = db.Query( runners.Runners, projection=['username'] )
            q.ancestor( runners.key() )
            for runner in q.run( limit=100000 ):
                q2 = db.Query( runs.Runs, 
                               projection=('game', 'category'),
                               distinct=True )
                q2.ancestor( runs.key() )
                q2.filter('username =', runner.username)
                num_pbs = q2.count( limit=1000 )
                runnerlist.append( 
                    dict( username = runner.username, num_pbs = num_pbs ) )
            runnerlist.sort( key=itemgetter('username') )
            runnerlist.sort( key=itemgetter('num_pbs'), reverse=True )
            if memcache.set( key, runnerlist ):
                logging.info("Set runnerlist in memcache")
            else:
                logging.warning("Failed to set new runnerlist in memcache")
        else:
            logging.info("Got runnerlist from memcache")
        return runnerlist

    def update_cache_runnerlist(self, runnerlist):
        key = self.get_runnerlist_memkey( )
        if memcache.set( key, runnerlist ):
            logging.info("Updated runnerlist in memcache")
        else:
            logging.error("Failed to update runnerlist in memcache")
