import webapp2
import os
import jinja2
import util
import runners
import runs
import logging

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
                q2 = db.Query(runs.Runs, projection=('game_code', 'time'))
                q2.ancestor(runs.key())
                q2.filter('username =', username)
                q2.filter('game =', run.game)
                q2.filter('category =', run.category)
                q2.order('time')
                pb = q2.get()
                pblist.append( 
                    dict( game = run.game, game_code = pb.game_code,
                          category = run.category, seconds = pb.time,
                          time = util.seconds_to_timestr( pb.time ) ) )
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
            logging.warning("Failed to set pblist for " + username 
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
                q2 = db.Query(runs.Runs, projection=['time'])
                q2.ancestor(runs.key())
                q2.filter('game_code =', game_code)
                q2.filter('category =', run.category)
                q2.filter('username =', run.username)
                q2.order('time')
                pb = q2.get()
                # Append the (user, time) to the category's list
                item = dict( username = run.username,
                             seconds = pb.time,
                             time = util.seconds_to_timestr( pb.time ) )
                runlist = rundict.get( run.category )
                if runlist:
                    runlist.append( item )
                else:
                    runlist = [ item ]
                rundict[ run.category ] = runlist

            # For each category, sort the runlist by time
            for category, runlist in rundict.iteritems():
                sorted_runlist = sorted( runlist, key=lambda k: k['seconds'] )
                rundict[ category ] = sorted_runlist

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
            logging.warning("Failed to set rundict for " + game_code 
                            + " in memcache")
