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
    RUNLIST_PAGE_LIMIT = 75
    GAMEPAGE_PAGE_LIMIT = 50
    PB_PAGE_LIMIT = 101
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

    def get_pblist_cursor_memkey( self, username, page_num ):
        return username + ":pblist:cursor-page-" + str( page_num )

    def get_pblist_memkey( self, username ):
        return username + ":pblist"

    # Similar to other stuff, returns a dict with page_num, has_next and 
    # pblist keys, or OVER_QUOTA_ERROR
    def get_pblist( self, username, page_num ):
        key = self.get_pblist_memkey( username )
        cached_pblists = memcache.get( key )
        if cached_pblists is None:
            cached_pblists = dict( )
        res = cached_pblists.get( page_num )
        if res is None:
            res = dict( page_num=page_num, has_next=False )
            # Not in memcache, so construct the pblist and store in memcache.
            # pblist is a list of dictionaries with 3 indices, 'game', 
            # 'game_code' and 'infolist'.  The infolist is another list of 
            # dictionaries containing all the info for each pb of the game.
            pblist = [ ]
            try:
                q = db.Query( runs.Runs,
                              projection=['game', 'category', 'seconds',
                                          'date', 'video', 'version'] )
                q.ancestor( runs.key() )
                q.filter( 'username =', username )
                q.order( 'game' )
                q.order( 'category' )
                q.order( 'seconds' )
                c = memcache.get( self.get_pblist_cursor_memkey(
                    username, page_num ) )
                if c:
                    try:
                        q.with_cursor( start_cursor=c )
                    except BadRequestError:
                        res['page_num'] = 1
                else:
                    res['page_num'] = 1
                cur_game = None
                cur_category = None
                info = None
                pb = None
                cursor_to_save = c
                last_cursor = None
                runs_queried = 0
                for run in q.run( limit = self.PB_PAGE_LIMIT ):
                    if run.game != cur_game:
                        # New game
                        pb = dict( game = run.game,
                                   game_code = util.get_code( run.game ),
                                   num_runs = 0,
                                   infolist = [ ] )
                        pblist.append( pb )
                        cur_game = run.game
                        cur_category = None

                    if run.category != cur_category:
                        # New category
                        info = dict( username = username,
                                     username_code = util.get_code( username ),
                                     category = run.category,
                                     category_code = util.get_code(
                                         run.category ),
                                     pb_seconds = run.seconds,
                                     pb_time = util.seconds_to_timestr(
                                         run.seconds ),
                                     pb_date = run.date,
                                     num_runs = 1,
                                     avg_seconds = run.seconds,
                                     avg_time = util.seconds_to_timestr(
                                         run.seconds, dec_places=0 ),
                                     video = run.video,
                                     version = run.version )
                        pb['infolist'].append( info )
                        cur_category = run.category
                        if last_cursor is not None:
                            cursor_to_save = last_cursor
                    else:
                        # Repeat game, category
                        info['num_runs'] += 1
                        info['avg_seconds'] += ( 1.0 / info['num_runs'] ) * (
                            run.seconds - info['avg_seconds'] )
                        info['avg_time'] = util.seconds_to_timestr(
                            info['avg_seconds'], dec_places=0 )
                    pb['num_runs'] += 1
                    runs_queried += 1
                    last_cursor = q.cursor( )
                
                if runs_queried >= self.PB_PAGE_LIMIT:
                    res['has_next'] = True

                    # Last category found is possibly incomplete, so remove
                    del pblist[ -1 ]['infolist'][ -1 ]
                    if len( pblist[ -1 ]['infolist'] ) <= 0:
                        del pblist[ -1 ]
                        if len( pblist ) <= 0:
                            # Too many runs for this game, category
                            pb = dict(
                                game = cur_game,
                                game_code = util.get_code( cur_game ),
                                num_runs = 0,
                                infolist = [ dict( 
                                    username=username,
                                    username_code = util.get_code(
                                        username ),
                                    category=( 'TOO MANY RUNS FOR '
                                               + 'CATEGORY: '
                                               + cur_category
                                               + ' (max is '
                                               + str( self.PB_PAGE_LIMIT - 1 )
                                               + ', please delete some runs)' ),
                                    category_code=util.get_code(
                                        cur_category ),
                                    pb_seconds=0,
                                    pb_time=util.seconds_to_timestr( 0 ),
                                    pb_date=None,
                                    num_runs=0,
                                    avg_seconds=0,
                                    avg_time=util.seconds_to_timestr( 0 ),
                                    video=None ) ] )
                            pblist.append( pb )

                cursor_key = self.get_pblist_cursor_memkey(
                    username, res['page_num'] + 1 )
                if memcache.set( cursor_key, cursor_to_save ):
                    logging.debug( 'Set ' + cursor_key + " in memcache" )
                else:
                    logging.warning( 'Failed to set ' + cursor_key
                                     + ' in memcache' )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            # Sort the categories for a game by num_runs
            for pb in pblist:
                pb['infolist'].sort( key=itemgetter('num_runs'), reverse=True )

            res['pblist'] = pblist
            cached_pblists[ res['page_num'] ] = res
            if memcache.set( key, cached_pblists ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return res

    def get_cached_pblists( self, username ):
        key = self.get_pblist_memkey( username )
        return memcache.get( key )

    def update_cache_pblist( self, username, cached_pblists ):
        key = self.get_pblist_memkey( username )
        if memcache.set( key, cached_pblists ):
            logging.debug( "Updated " + key + " in memcache" )
        else:
            logging.error( "Failed to update " + key + " in memcache" )

    def get_gamepage_cursor_memkey( self, game, category_code, page_num ):
        return game + ":" + category_code + ":page-cursor-" + str( page_num )

    def get_gamepage_memkey( self, game, category_code ):
        return game + ":" + category_code + ":gamepage"

    # On success, returns a dictionary 'gamepage' containing 3 entries:
    # gamepage['has_next']: True if there's a next page, false otherwise
    # gamepage['page_num']: The page num for this result
    # gamepage['d']: Dictionary object containing run info for this game and
    #                category_code and page_num
    # On failure, returns self.OVER_QUOTA_ERROR
    def get_gamepage( self, game, category, page_num ):
        if category is None:
            return dict( has_next=False, page_num=0, d=None )

        category_code = util.get_code( category )
        key = self.get_gamepage_memkey( game, category_code )
        cached_gamepages = memcache.get( key )
        if cached_gamepages is None:
            cached_gamepages = dict( )
        gamepage = cached_gamepages.get( page_num )
        if gamepage is None:
            # Not in memcache, so construct the gamepage and store it in 
            # memcache.
            # gamepage['d'] has up to 7 keys:
            # 'category', 'category_code', 'bk_runner', 'bk_time',
            # 'bk_date', 'bk_video' and 'infolist'.
            gamepage = dict( page_num=page_num,
                             has_next=True )
            d = dict( category=category,
                      category_code=category_code,
                      infolist=[ ] )

            # Grab the game model
            game_model = self.get_game_model( util.get_code( game ) )
            if game_model is None:
                logging.error( "Could not create " + key + " due to no "
                               + "game model" )
                return dict( has_next=False, page_num=0, d=None )
            if game_model == self.OVER_QUOTA_ERROR:
                return self.OVER_QUOTA_ERROR
            gameinfolist = json.loads( game_model.info )

            # Check for a best known time for this category
            for gameinfo in gameinfolist:
                if gameinfo['category'] == category:
                    d['bk_runner'] = gameinfo.get( 'bk_runner' )
                    d['bk_time'] = util.seconds_to_timestr(
                        gameinfo.get( 'bk_seconds' ) )
                    d['bk_date'] = util.datestr_to_date( 
                        gameinfo.get( 'bk_datestr' ) )[ 0 ]
                    d['bk_video'] = gameinfo.get( 'bk_video' )
                    break
            try:
                # Get 1 run per username
                q = db.Query( runs.Runs,
                              projection=['username', 'seconds',
                                          'date', 'video', 'version'] )
                q.ancestor( runs.key() )
                q.filter( 'game =', game )
                q.filter( 'category =', category )
                q.order( 'seconds' )
                q.order( 'date' )
                usernames_seen = set( )
                cached_cursor = memcache.get( self.get_gamepage_cursor_memkey(
                    game, category_code, page_num ) )
                if cached_cursor:
                    try:
                        q.with_cursor( start_cursor=cached_cursor['c'] )
                        usernames_seen = cached_cursor['usernames_seen']
                    except BadRequestError:
                        gamepage['page_num'] = page_num
                else:
                    gamepage['page_num'] = 1
                num_runs = 0
                for run in q.run( limit = self.GAMEPAGE_PAGE_LIMIT ):
                    num_runs += 1
                    if run.username in usernames_seen:
                        continue
                    # Add the info to the gamepage
                    info = dict( username = run.username,
                                 username_code = util.get_code(
                                     run.username ),
                                 category = category,
                                 category_code = category_code,
                                 pb_seconds = run.seconds,
                                 pb_time = util.seconds_to_timestr(
                                     run.seconds ),
                                 pb_date = run.date,
                                 video = run.video,
                                 version = run.version )
                    d['infolist'].append( info )
                    usernames_seen.add( run.username )
                if num_runs < self.GAMEPAGE_PAGE_LIMIT:
                    gamepage['has_next'] = False
                else:
                    c = q.cursor( )
                    cached_cursor = dict( c=c, usernames_seen=usernames_seen )
                    cursor_key = self.get_gamepage_cursor_memkey(
                        game, category_code, gamepage['page_num'] + 1 )
                    if memcache.set( cursor_key, cached_cursor ):
                        logging.debug( "Set " + cursor_key + " in memcache" )
                    else:
                        logging.warning( "Failed to set new " + cursor_key
                                         + " in memcache" )
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            gamepage['d'] = d
            cached_gamepages[ gamepage['page_num'] ] = gamepage
            if memcache.set( key, cached_gamepages ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return gamepage

    # Returns a dictionary where keys are page_nums and entries are
    # objects returned by get_gamepage( game, category, page_num )
    def get_cached_gamepages( self, game, category_code ):
        key = self.get_gamepage_memkey( game, category_code )
        return memcache.get( key )

    def update_cache_gamepage( self, game, category_code, cached_gamepages ):
        key = self.get_gamepage_memkey( game, category_code )
        if memcache.set( key, cached_gamepages ):
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
            
    def get_runlist_for_runner_cursor_memkey( self, username, page_num ):
        return username + ":runlist_for_runner:cursor-page-" + str( page_num )

    def get_runlist_for_runner_memkey( self, username ):
        return username + ":runlist_for_runner"

    # Similar to other get methods here, returns a dict with page_num, has_next
    # and runlist keys on success, or OVER_QUOTA_ERROR on failure
    def get_runlist_for_runner( self, username, page_num ):
        key = self.get_runlist_for_runner_memkey( username )
        cached_runlists = memcache.get( key )
        if cached_runlists is None:
            cached_runlists = dict( )
        res = cached_runlists.get( page_num )
        if res is None:
            # Not in memcache, so construct the runlist and store in memcache.
            res = dict( page_num=page_num,
                        has_next=True )
            runlist = [ ]
            try:
                q = runs.Runs.all( )
                q.ancestor( runs.key() )
                q.filter( 'username =', username )
                q.order( '-date' )
                q.order( '-datetime_created' )
                c = memcache.get( self.get_runlist_for_runner_cursor_memkey(
                    username, page_num ) )
                if c:
                    try:
                        q.with_cursor( start_cursor=c )
                    except BadRequestError:
                        res['page_num'] = 1
                else:
                    res['page_num'] = 1
                for run in q.run( limit = self.RUNLIST_PAGE_LIMIT ):
                    runlist.append( dict(
                        run_id = str( run.key().id() ),
                        game = run.game,
                        game_code = util.get_code( run.game ),
                        category = run.category,
                        category_code = util.get_code( run.category ),
                        time = util.
                        seconds_to_timestr( run.seconds ),
                        date = run.date,
                        datetime_created = run.datetime_created,
                        video = run.video,
                        version = run.version,
                        notes = run.notes ) )
                c = q.cursor( )
                cursor_key = self.get_runlist_for_runner_cursor_memkey(
                    username, res['page_num'] + 1 )
                if memcache.set( cursor_key, c ):
                    logging.debug( "Set " + cursor_key + " in memcache" )
                else:
                    logging.warning( "Failed to set new " + cursor_key
                                     + " in memcache" )
                if len( runlist ) < self.RUNLIST_PAGE_LIMIT:
                    res['has_next'] = False
            except apiproxy_errors.OverQuotaError, msg:
                logging.error( msg )
                return self.OVER_QUOTA_ERROR

            res['runlist'] = runlist
            cached_runlists[ res['page_num'] ] = res
            if memcache.set( key, cached_runlists ):
                logging.debug( "Set " + key + " in memcache" )
            else:
                logging.warning( "Failed to set " + key + " in memcache" )
        else:
            logging.debug( "Got " + key + " from memcache" )
        return res

    def get_cached_runlists_for_runner( self, username ):
        key = self.get_runlist_for_runner_memkey( username )
        return memcache.get( key )

    def update_cache_runlist_for_runner( self, username, cached_runlists ):
        key = self.get_runlist_for_runner_memkey( username )
        if memcache.set( key, cached_runlists ):
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
