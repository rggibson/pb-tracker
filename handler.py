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
                return runners.Runners.get_by_id(long(user_id))

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
                q2 = runs.Runs.all()
                q2.filter('username =', username)
                q2.filter('game =', run.game)
                q2.filter('category =', run.category)
                q2.order('time')
                pb = q2.get()
                pblist.append( 
                    dict( game = pb.game, category = pb.category,
                          seconds = pb.time,
                          time = util.seconds_to_timestr( pb.time ) ) )
            logging.info("Created pblist for " + username)
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
