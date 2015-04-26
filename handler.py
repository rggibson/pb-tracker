# handler.py
# Author: Richard Gibson
#
# The base class for all the other handlers.  Contains some useful rendering
# and login functions.  The majority of the class contains functions that
# perform common queries throughout the code, many of which are explained in 
# their needed classes. 
#

import webapp2
import os
import jinja2
import util
import runners
import runs
import games
import logging
import json
import time

from operator import itemgetter

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.runtime import apiproxy_errors
from google.appengine.ext.db import BadRequestError

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join
                                   (os.path.dirname(__file__), 
                                    'templates')), autoescape = True)


class Handler(webapp2.RequestHandler):
    PAGE_LIMIT = 50
    OVER_QUOTA_ERROR = 'OVER_QUOTA_ERROR'

    # Writing and rendering utility functions
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = JINJA_ENVIRONMENT.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_json( self, obj ):
        self.response.headers[ 'Content-Type' ] = ( 'application/json; ' 
                                                    + 'charset=UTF-8' )
        # Allow javascript from any domain to access the JSON
#        self.response.headers.add_header( 'Access-Control-Allow-Origin', '*' )
        self.write( json.dumps( obj, cls = util.MyJSONEncoder ) )

    # Helpful override to determine the format of the output
    def initialize( self, *a, **kw ):
        webapp2.RequestHandler.initialize( self, *a, **kw )
        if self.request.path.endswith( '.json' ):
            self.format = 'json'
        else:
            self.format = 'html'

    # User login functions
    def is_valid_login( self, username, password ):
        username_code = util.get_code( username )
        
        # Find the user in the database
        try:
            user = runners.Runners.get_by_key_name( username_code, 
                                                    parent=runners.key() )
        except apiproxy_errors.OverQuotaError, msg:
            logging.error( msg )
            return False, dict( user_error="Over quota error" )

        if not user:
            return False, dict( user_error="Username not found" )

        # Check for valid password
        if util.valid_pw( username_code, password, user.password ):
            return True, dict( )
        else:
            return False, dict( pass_error="Invalid password" )

    def login( self, user_id ):
        cookie = 'user_id={0};Path=/'.format( util.make_secure_val
                                              ( str(user_id) ) )
        self.response.headers.add_header( 'Set-Cookie', cookie )

    def get_user( self ):
        cookie_val = self.request.cookies.get( 'user_id' )
        if cookie_val:
            username_code = util.check_secure_val( cookie_val )
            if username_code:
                try:
                    user = runners.Runners.get_by_key_name( 
                        username_code, parent=runners.key() )
                except apiproxy_errors.OverQuotaError, msg:
                    logging.error( msg )
                    return self.OVER_QUOTA_ERROR
                return user

    # Memcache / Datastore functions
    def get_runner_memkey( self, username_code ):
        return username_code + ":runner"

    def get_runner( self, username_code ):
        if not username_code:
            return None

        key = self.get_runner_memkey( username_code )
        runner = memcache.get( key )
        if runner is None:
            # Not in memcache, so check the database
            try:
                runner = runners.Runners.get_by_key_name( username_code,
                                                          parent=runners.key() )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
            if memcache.set( key, runner ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return runner

    def update_cache_runner( self, username_code, runner ):
        key = self.get_runner_memkey( username_code )
        if memcache.set( key, runner ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_game_model_memkey( self, game_code ):
        return game_code + ":game_model"

    def get_game_model( self, game_code ):
        if not game_code:
            return None

        key = self.get_game_model_memkey( game_code )
        game_model = memcache.get( key )
        if game_model is None:
            # Not in memcache, so get the game from datastore
            try:
                game_model = games.Games.get_by_key_name( game_code,
                                                          parent=games.key() )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
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

    def get_categories_memkey( self ):
        return "categories"

    def get_categories( self, no_refresh=False ):
        key = self.get_categories_memkey( )
        categories = memcache.get( key )
        if categories is None and not no_refresh:
            # Not in memcache, so get the categories for every game
            categories = dict( )
            try:
                q = db.Query( games.Games )
                q.ancestor( games.key() )
                for game_model in q.run( limit=10000 ):
                    gameinfolist = json.loads( game_model.info )
                    categories[ str( game_model.game ) ] = [ ]
                    for gameinfo in gameinfolist:
                        categories[ str( game_model.game ) ].append( 
                            str( gameinfo['category'] ) )
                    # Sort the categories for each game in alphabetical order
                    categories[ str( game_model.game ) ].sort( )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
            if memcache.set( key, categories ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif categories is not None:
            logging.debug( "Got " + key + " from memcache" )
        return categories

    def update_cache_categories( self, categories ):
        key = self.get_categories_memkey( )
        if memcache.set( key, categories ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_run_by_id_memkey( self, run_id ):
        return str( run_id ) + ":run"

    def get_run_by_id( self, run_id ):
        key = self.get_run_by_id_memkey( run_id )
        run = memcache.get( key )
        if run is None:
            # Not in memcache, so get the run from database and store in
            # memcache.
            try:
                run = runs.Runs.get_by_id( long( run_id ), parent=runs.key() )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
            if memcache.set( key, run ):
                logging.debug( "Set run in memcache for run_id" 
                               + str( run_id ) )
            else:
                logging.warning( "Failed to set new run for run_id" 
                                 + str( run_id ) + " in memcache" )
        else:
            logging.debug( "Got run with run_id " + str( run_id ) + " from "
                           + "memcache" )
        return run

    def update_cache_run_by_id( self, run_id, run ):
        key = self.get_run_by_id_memkey( run_id )
        if memcache.set( key, run ):
            logging.debug( "Updated run for run_id " + str( run_id ) 
                          + " in memcache" )
        else:
            logging.error( "Failed to update run for run_id " 
                           + str( run_id ) + " in memcache" )

    def get_runinfo_memkey( self, username, game, category ):
        return username + ":" + game + ":" + category + ":runinfo"

    def get_runinfo( self, username, game, category, no_refresh=False ):
        key = self.get_runinfo_memkey( username, game, category )
        runinfo = memcache.get( key )
        if runinfo is None and not no_refresh:
            # Not in memcache, so constrcut the runinfo dictionary
            pb_run = None
            avg_seconds = 0
            num_runs = 0
            try:
                q = db.Query( runs.Runs, 
                              projection=('seconds', 'date', 'video',
                                          'version') )
                q.ancestor( runs.key() )
                q.filter('username =', username)
                q.filter('game =', game)
                q.filter('category =', category)
                q.order('-date') # Cut off old runs
                for run in q.run( limit = 100000 ):
                    num_runs += 1
                    avg_seconds += ( 1.0 / num_runs ) * ( 
                        run.seconds - avg_seconds )
                    if( pb_run is None or run.seconds <= pb_run.seconds ):
                        pb_run = run

                runinfo = dict( username = username,
                                username_code = util.get_code( username ),
                                category = category, 
                                category_code = util.get_code( category ),
                                pb_seconds = None,
                                pb_time = None,
                                pb_date = None,
                                num_runs = num_runs,
                                avg_seconds = avg_seconds,
                                avg_time = util.seconds_to_timestr(
                                    avg_seconds, dec_places=0),
                                video = None )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
            # Set the pb time
            if pb_run:
                runinfo['pb_seconds'] = pb_run.seconds
                runinfo['pb_time'] = util.seconds_to_timestr( pb_run.seconds )
                runinfo['pb_date'] = pb_run.date
                runinfo['video'] = pb_run.video
                runinfo['version'] = pb_run.version
                
            if memcache.set( key, runinfo ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif runinfo is not None:
            logging.debug( "Got " + key + " from memcache" )
        return runinfo
            
    def update_cache_runinfo( self, username, game, category, runinfo ):
        key = self.get_runinfo_memkey( username, game, category )
        if memcache.set( key, runinfo ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_pblist_memkey( self, username ):
        return username + ":pblist"

    def get_pblist( self, username, no_refresh=False ):
        key = self.get_pblist_memkey( username )
        pblist = memcache.get( key )
        if pblist is None and not no_refresh:
            # Not in memcache, so construct the pblist and store in memcache.
            # pblist is a list of dictionaries with 3 indices, 'game', 
            # 'game_code' and 'infolist'.  The infolist is another list of 
            # dictionaries containing all the info for each pb of the game.
            pblist = [ ]
            try:
                # Use a projection query to get all of the unique game, category
                # pairs
                q = db.Query( runs.Runs, projection=('game', 'category'), 
                              distinct=True )
                q.ancestor( runs.key() )
                q.filter( 'username =', username )
                q.order( 'game' )
                q.order( 'category' )
                cur_game = None
                for run in q.run( limit = 1000 ):
                    if run.game != cur_game:
                        # New game
                        pb = dict( game = run.game, 
                                   game_code = util.get_code( run.game ),
                                   num_runs = 0,
                                   infolist = [ ] )
                        pblist.append( pb )
                        cur_game = run.game                

                    # Add runinfo to pblist
                    info = self.get_runinfo( username, run.game, run.category )
                    if info == self.OVER_QUOTA_ERROR:
                        return self.OVER_QUOTA_ERROR
                    pb['infolist'].append( info )
                    pb['num_runs'] += info['num_runs']
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            # Sort the categories for a game by num_runs
            for pb in pblist:
                pb['infolist'].sort( key=itemgetter('num_runs'), reverse=True )

            # Sort the games by number of runs
            pblist.sort( key=itemgetter('num_runs'), reverse=True )

            if memcache.set( key, pblist ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif pblist is not None:
            logging.debug( "Got " + key + " from memcache" )
        return pblist

    def update_cache_pblist( self, username, pblist ):
        key = self.get_pblist_memkey( username )
        if memcache.set( key, pblist ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_gamepage_memkey( self, game ):
        return game + ":gamepage"

    def get_gamepage( self, game, no_refresh=False ):
        key = self.get_gamepage_memkey( game )
        gamepage = memcache.get( key )
        if gamepage is None and not no_refresh:
            # Not in memcache, so construct the gamepage and store it in 
            # memcache.
            # Gamepage is a list of dictionaries. These dictionaries have up
            # to 5 keys, 'category', 'bk_runner', 'bk_time', 'bk_video' and
            # 'infolist'.
            gamepage = [ ]

            # Grab the game model
            game_model = self.get_game_model( util.get_code( game ) )
            if game_model is None:
                logging.error( "Could not create " + key + " due to no "
                               + "game model" )
                return None
            if game_model == self.OVER_QUOTA_ERROR:
                return self.OVER_QUOTA_ERROR
            gameinfolist = json.loads( game_model.info )

            try:
                # Use a projection query to get all of the unique 
                # username, category pairs
                q = db.Query( runs.Runs, projection=('username', 'category'), 
                              distinct=True )
                q.ancestor( runs.key() )
                q.filter( 'game =', game )
                q.order( 'category' )
                cur_category = None
                for run in q.run( limit = 1000 ):
                    if run.category != cur_category:
                        # New category
                        d = dict( category=run.category, 
                                  category_code=util.get_code( run.category ), 
                                  infolist=[ ] )
                        gamepage.append( d )
                        cur_category = run.category
                        # Check for a best known time for this category
                        for gameinfo in gameinfolist:
                            if gameinfo['category'] == run.category:
                                d['bk_runner'] = gameinfo.get( 'bk_runner' )
                                d['bk_time'] = util.seconds_to_timestr(
                                    gameinfo.get( 'bk_seconds' ) )
                                d['bk_date'] = util.datestr_to_date( 
                                    gameinfo.get( 'bk_datestr' ) )[ 0 ]
                                d['bk_video'] = gameinfo.get( 'bk_video' )
                                break

                    # Add the info to the gamepage
                    info = self.get_runinfo( run.username, game, run.category )
                    if info == self.OVER_QUOTA_ERROR:
                        return self.OVER_QUOTA_ERROR
                    d['infolist'].append( info )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
                
            # For each category, sort the runlist by seconds, breaking ties
            # by date
            for runlist in gamepage:
                runlist['infolist'].sort( key=lambda x: util.get_valid_date(
                        x['pb_date'] ) )
                runlist['infolist'].sort( key=itemgetter('pb_seconds') )
            
            # Sort the categories by number of runners
            gamepage.sort( key=lambda x: len(x['infolist']), reverse=True )

            if memcache.set( key, gamepage ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif gamepage is not None:
            logging.debug( "Got " + key + " from memcache" )
        return gamepage

    def update_cache_gamepage( self, game, gamepage ):
        key = self.get_gamepage_memkey( game )
        if memcache.set( key, gamepage ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_gamelist_cursor_memkey( self, page_num ):
        return "gamelist-cursor:page-" + str( page_num )

    def get_gamelist_memkey( self ):
        return "gamelist"

    # On succes, returns a dict res with the following entries:
    # res['has_next'] - boolean indicating whether there's a next page
    # res['page_num'] - the page num for the results returned
    # res['gamelist'] - the gamelist for this page_num
    # May fail and return OVER_QUOTA_ERROR
    def get_gamelist( self, page_num ):
        key = self.get_gamelist_memkey( )
        data = memcache.get( key )
        if data is None:
            data = dict( )
        res = data.get( page_num )
        if res is None:
            # Build the gamelist, which is a list of dictionaries where each
            # dict gives the game, game_code and number of pbs for that game.
            # The list is sorted by numbers of pbs for the game
            res = dict( page_num=page_num )
            gamelist = [ ]
            projection = [ 'game', 'num_pbs' ]
            try:
                q = db.Query( games.Games, projection=projection )
                q.ancestor( games.key() )
                q.order( '-num_pbs' )
                q.order( 'game' )
                c = memcache.get( self.get_gamelist_cursor_memkey( page_num ) )
                if c:
                    try:
                        q.with_cursor( start_cursor=c )
                    except BadRequestError:
                        res['page_num'] = 1
                else:
                    # Send the user back to the first page
                    res['page_num'] = 1
                for game_model in q.run( limit=self.PAGE_LIMIT ):
                    if game_model.num_pbs <= 0:
                        break
                    d = dict( game = game_model.game,
                              game_code = util.get_code( game_model.game ),
                              num_pbs = game_model.num_pbs )
                    gamelist.append( d )
                c = q.cursor( )
                cursor_key = self.get_gamelist_cursor_memkey(
                    res['page_num'] + 1 )
                if memcache.set( cursor_key, c ):
                    logging.debug( "Set " + cursor_key + " in memcache" )
                else:
                    logging.warning( "Failed to set new " + cursor_key
                                     + " in memcache" )
                if len( gamelist ) >= self.PAGE_LIMIT:
                    res['has_next'] = True
                else:
                    res['has_next'] = False
                res['gamelist'] = gamelist
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            data[ res['page_num'] ] = res
            if memcache.set( key, data ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set new " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return res

    # Returns a dictionary where keys are page_nums and entries are
    # objects returned by get_gamelist( page_num )
    def get_cached_gamelists( self ):
        key = self.get_gamelist_memkey( )
        return memcache.get( key )

    def update_cache_gamelist( self, data ):
        key = self.get_gamelist_memkey( )
        if memcache.set( key, data ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_static_gamelist_memkey( self ):
        return 'static-gamelist'

    def get_static_gamelist( self ):
        key = self.get_static_gamelist_memkey( )
        static_gl = memcache.get( key )
        if static_gl is None:
            static_gl = [ ]
            with open( 'json/gamelist.json', 'r' ) as data_file:
                data = json.load( data_file )
                for game_code, game in data['data'].iteritems( ):
                    static_gl.append( str( game ) )
            static_gl.sort( )
            if memcache.set( key, static_gl ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return static_gl

    def get_runnerlist_cursor_memkey( self, page_num ):
        return "runnerlist-cursor:page-" + str( page_num )

    def get_runnerlist_memkey( self ):
        return "runnerlist"

    # On succes, returns a dict res with the following entries:
    # res['has_next'] - boolean indicating whether there's a next page
    # res['page_num'] - the page num for the results returned
    # res['runnerlist'] - the runnerlist for this page_num
    # May fail and return OVER_QUOTA_ERROR
    def get_runnerlist( self, page_num ):
        key = self.get_runnerlist_memkey( )
        data = memcache.get( key )
        if data is None:
            data = dict( )
        res = data.get( page_num )
        if res is None:
            # Build the runnerlist, which is a list of dictionaries where each
            # dict gives the username and number of pbs for that user.
            # The list is sorted by numbers of pbs for the user.
            res = dict( page_num=page_num,
                        runnerlist=[ ],
                        has_next=True )
            try:
                q = db.Query( runners.Runners, 
                              projection=['username', 'gravatar', 'num_pbs'] )
                q.ancestor( runners.key() )
                q.order( '-num_pbs' )
                q.order( 'username' )
                c = memcache.get( self.get_runnerlist_cursor_memkey(
                    page_num ) )
                if c:
                    try:
                        q.with_cursor( start_cursor=c )
                    except BadRequestError:
                        res['page_num'] = 1
                else:
                    res['page_num'] = 1
                for runner in q.run( limit=self.PAGE_LIMIT ):
                    res['runnerlist'].append( 
                        dict( username = runner.username,
                              username_code = util.get_code( runner.username ),
                              num_pbs = runner.num_pbs,
                              gravatar_url = util.get_gravatar_url( 
                                  runner.gravatar ) ) )
                c = q.cursor( )
                cursor_key = self.get_runnerlist_cursor_memkey(
                    res['page_num'] + 1 )
                if memcache.set( cursor_key, c ):
                    logging.debug( "Set " + cursor_key + " in memcache" )
                else:
                    logging.warning( "Failed to set new " + cursor_key
                                     + " in memcache" )
                if len( res['runnerlist'] ) < self.PAGE_LIMIT:
                    res['has_next'] = False
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            data[ res['page_num'] ] = res
            if memcache.set( key, data ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set new " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return res

    # Returns a dictionary where keys are page_nums and entries are
    # objects returned by get_runnerlist( page_num )
    def get_cached_runnerlists( self ):
        key = self.get_runnerlist_memkey( )
        return memcache.get( key )

    def update_cache_runnerlist( self, runnerlists ):
        key = self.get_runnerlist_memkey( )
        if memcache.set( key, runnerlists ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_runlist_for_runner_memkey( self, username ):
        return username + ":runlist_for_runner"

    def get_runlist_for_runner( self, username, no_refresh=False ):
        key = self.get_runlist_for_runner_memkey( username )
        runlist = memcache.get( key )
        if runlist is None and not no_refresh:
            # Not in memcache, so construct the runlist and store in memcache.
            runlist = [ ]
            try:
                q = runs.Runs.all( )
                q.ancestor( runs.key() )
                q.filter( 'username =', username )
                q.order( '-date' )
                q.order( '-datetime_created' )
                for run in q.run( limit = 1000 ):
                    runlist.append( dict( run_id = str( run.key().id() ),
                                          game = run.game,
                                          game_code = util.get_code( run.game ),
                                          category = run.category,
                                          category_code = util.get_code( 
                                              run.category ),
                                          time = util.
                                          seconds_to_timestr( run.seconds ),
                                          date = run.date,
                                          datetime_created = run.datetime_created,
                                          video = run.video,
                                          version = run.version,
                                          notes = run.notes ) )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            if memcache.set( key, runlist ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif runlist is not None:
            logging.debug( "Got " + key + " from memcache" )
        return runlist

    def update_cache_runlist_for_runner( self, username, runlist ):
        key = self.get_runlist_for_runner_memkey( username )
        if memcache.set( key, runlist ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_user_has_run_memkey( self, username, game ):
        return username + ":" + game + ":user_has_run"

    def get_user_has_run( self, username, game, no_refresh=False ):
        key = self.get_user_has_run_memkey( username, game )
        user_has_run = memcache.get( key )
        if user_has_run is None and not no_refresh:
            # Not in memcache, so check datastore
            try:
                q = db.Query( runs.Runs, keys_only=True )
                q.ancestor( runs.key() )
                q.filter( 'username =', username )
                q.filter( 'game =', game )
                num = q.count( limit=1 )
                if num > 0:
                    user_has_run = True
                else:
                    user_has_run = False
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR
            if memcache.set( key, user_has_run ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif user_has_run is not None:
            logging.debug( "Got " + key + " from memcache" )
        return user_has_run

    def update_cache_user_has_run( self, username, game, user_has_run ):
        key = self.get_user_has_run_memkey( username, game )
        if memcache.set( key, user_has_run ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_last_run_memkey( self, username ):
        return username + ":last_run"

    def get_last_run( self, username, no_refresh=False ):
        key = self.get_last_run_memkey( username )
        run = memcache.get( key )
        if run is None and not no_refresh:
            # Not in memcache, so check datastore
            try:
                q = db.Query( runs.Runs )
                q.ancestor( runs.key() )
                q.filter( 'username =', username )
                q.order( '-datetime_created' )
                run = q.get( )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            if memcache.set( key, run ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        elif run is not None:
            logging.debug( "Got " + key + " from memcache" )
        return run
        
    def update_cache_last_run( self, username, run ):
        key = self.get_last_run_memkey( username )
        if memcache.set( key, run ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )
