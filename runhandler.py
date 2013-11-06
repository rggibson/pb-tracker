# runhandler.py
# Author: Richard Gibson
#
# A base class for the submit.Submit and deleterun.DeleteRun classes.  The 
# majority of the functions in this class contain functions that update 
# memcache upon deletion / insertion of runs into the database.  If we didn't
# care about datastore reads/writes, this class would not be necessary. 
# However, I would like to continue to use the free tier usage of GAE as long
# as possible, hence these optimization routines to stay off the database as
# much as possible. 
#

import handler
import util
import games
import runs
import logging
import json

from operator import itemgetter
from google.appengine.ext import db

class RunHandler( handler.Handler ):
    def num_runs( self, username, game, category, limit ):
        q = db.Query( runs.Runs, keys_only=True )
        q.ancestor( runs.key() )
        q.filter( 'username =', username )
        q.filter( 'game =', game )
        q.filter( 'category =', category )
        return q.count( limit=limit )

    def update_runner( self, runner, delta_num_pbs ):
        if delta_num_pbs != 0:
            runner.num_pbs += delta_num_pbs
            runner.put( )
            self.update_cache_runner( util.get_code( runner.username ),
                                      runner )

    def update_games_put( self, params, delta_num_pbs ):
        user = params['user']
        game_model = params['game_model']
        game = params['game']
        category = params['category']
        game_code = params['game_code']
        category_found = params['category_found']
        seconds = params['seconds']
        datestr = params['datestr']
        video = params['video']
        is_bkt = params['is_bkt']

        if game_model is None:
            # Add a new game to the database
            d = dict( category=category, bk_runner=None, bk_seconds=None,
                      bk_datestr=None, bk_video=None, bk_updater=None )
            if is_bkt:
                d['bk_runner'] = user.username
                d['bk_seconds'] = seconds
                d['bk_datestr'] = datestr
                d['bk_video'] = video
                d['bk_updater'] = user.username
            game_model = games.Games( game = game,
                                      info = json.dumps( [ d ] ),
                                      num_pbs = 1,
                                      parent = games.key(),
                                      key_name = game_code )
            game_model.put( )
            logging.warning( "Put new game " + game + " with "
                             + " category " + category + " in database." )

            # Update memcache
            self.update_cache_game_model( game_code, game_model )
            categories = self.get_categories( no_refresh=True )
            if categories is not None:
                categories[ str( game ) ] = [ str( category ) ]
                self.update_cache_categories( categories )

            return

        game_model.num_pbs += delta_num_pbs

        if not category_found:
            # Add a new category for this game in the database
            info = json.loads( game_model.info )
            d = dict( category=category, bk_runner=None, bk_seconds=None,
                      bk_video=None )
            if is_bkt:
                d['bk_runner'] = user.username
                d['bk_seconds'] = seconds
                d['bk_datestr'] = datestr
                d['bk_video'] = video
                d['bk_updater'] = user.username
            info.append( d )
            game_model.info = json.dumps( info )
            game_model.put( )
            logging.debug( "Added category " + category + " to game " 
                           + game + " in database." )

            # Update memcache
            self.update_cache_game_model( game_code, game_model )
            categories = self.get_categories( no_refresh=True )
            if categories is not None:
                categories[ str( game ) ].append( str( category ) )
                categories[ str( game ) ].sort( )
                self.update_cache_categories( categories )

            return

        if is_bkt:
            # Update the best known time for this game, category
            gameinfolist = json.loads( game_model.info )
            for gameinfo in gameinfolist:
                if gameinfo['category'] == category:
                    gameinfo['bk_runner'] = user.username
                    gameinfo['bk_seconds'] = seconds
                    gameinfo['bk_datestr'] = datestr
                    gameinfo['bk_video'] = video
                    gameinfo['bk_updater'] = user.username
                    game_model.info = json.dumps( gameinfolist )
                    logging.debug( "Updated best known time for game "
                                   + game + ", category " + category 
                                   + " in database" )
                    break

        if is_bkt or delta_num_pbs != 0:
            # We made some changes, so store in db and update memcache
            game_model.put( )
            self.update_cache_game_model( game_code, game_model )

    def update_games_delete( self, game_model, delta_num_pbs ):
        if delta_num_pbs != 0:
            game_model.num_pbs += delta_num_pbs
            game_model.put( )
            self.update_cache_game_model( util.get_code( game_model.game ), 
                                          game_model )

    def update_runinfo_put( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        date = params[ 'date' ]
        video = params[ 'video' ]
        version = params[ 'version' ]

        # Update runinfo in memcache
        runinfo = self.get_runinfo( user.username, game, category, 
                                    no_refresh=True )
        if runinfo is None:
            return

        runinfo['num_runs'] += 1
        runinfo['avg_seconds'] += ( ( 1.0 / runinfo['num_runs'] ) 
                                    * ( seconds - runinfo['avg_seconds'] ) )
        runinfo['avg_time'] = util.seconds_to_timestr( 
            runinfo['avg_seconds'] )
        if( runinfo['pb_seconds'] is None 
            or runinfo['pb_seconds'] > seconds ):
            # We need to update pb as well
            runinfo['pb_seconds'] = seconds
            runinfo['pb_time'] = time
            runinfo['pb_date'] = date
            runinfo['video'] = video
            runinfo['version'] = version
        self.update_cache_runinfo( user.username, game, category, runinfo )

    def update_runinfo_delete( self, user, old_run ):
        # Update avg, num runs
        runinfo = self.get_runinfo( user.username, old_run['game'],
                                    old_run['category'], no_refresh=True )
        if runinfo is None:
            return

        if runinfo['num_runs'] <= 0:
            logging.error( "Failed to update runinfo due to nonpositive "
                           + "num_runs " + str( runinfo['num_runs'] ) )
            self.update_cache_runinfo( user.username, old_run['game'],
                                       old_run['category'], None )
            return

        if( runinfo['num_runs'] > 1 ):
            runinfo['avg_seconds'] -= ( 1.0 * old_run['seconds'] 
                                        / runinfo['num_runs'] )
            runinfo['num_runs'] -= 1
            runinfo['avg_seconds'] *= ( 1.0 * ( runinfo['num_runs'] + 1 ) 
                                        / runinfo['num_runs'] )
            runinfo['avg_time'] = util.seconds_to_timestr( 
                runinfo['avg_seconds'] )
            if( runinfo['pb_seconds'] == old_run['seconds'] ):
                # We need to replace the pb too
                q = db.Query( runs.Runs, projection=('seconds', 'date', 
                                                     'video', 'version') )
                q.ancestor( runs.key() )
                q.filter( 'username =', user.username )
                q.filter( 'game =', old_run['game'] )
                q.filter( 'category =', old_run['category'] )
                q.order( 'seconds' )
                q.order( 'date' )
                pb_run = q.get( )
                if pb_run:
                    runinfo['pb_seconds'] = pb_run.seconds
                    runinfo['pb_time'] = util.seconds_to_timestr( 
                        pb_run.seconds )
                    runinfo['pb_date'] = pb_run.date
                    runinfo['video'] = pb_run.video
                    runinfo['version'] = pb_run.version
                else:
                    logging.error( "Unable to update runinfo due to no new "
                                   + "pb found" )
                    self.update_cache_runinfo( user.username, old_run['game'],
                                               old_run['category'], None )
                    return
            self.update_cache_runinfo( user.username, old_run['game'],
                                       old_run['category'], runinfo )
        else:
            # No other runs for game, category combo
            self.update_cache_runinfo( user.username, old_run['game'],
                                       old_run['category'], 
                                       dict( username=user.username,
                                             username_code=util.get_code(
                                                 user.username ),
                                             category=old_run['category'],
                                             category_code=util.get_code(
                                                 old_run['category'] ),
                                             pb_seconds=None,
                                             pb_time=None,
                                             pb_date=None,
                                             num_runs=0,
                                             avg_seconds=0,
                                             avg_time='0:00',
                                             video=None,
                                             version=None ) )

    def update_pblist_put( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        game_code = params[ 'game_code' ]

        # Update pblist in memcache
        pblist = self.get_pblist( user.username, no_refresh=True )
        if pblist is None:
            return

        for pb in pblist:
            if( pb['game'] == game ):
                pb['num_runs'] += 1
                pblist.sort( key=itemgetter('game') )
                pblist.sort( key=itemgetter('num_runs'), reverse=True )
                for i, info in enumerate( pb['infolist'] ):
                    if( info['category'] == category ):
                        pb['infolist'][i] = self.get_runinfo( user.username, 
                                                              game, category )
                        pb['infolist'].sort( key=itemgetter('category') )
                        pb['infolist'].sort( key=itemgetter('num_runs'),
                                             reverse=True )
                        self.update_cache_pblist( user.username, pblist )
                        return

                # User has run this game, but not this category.
                # Add the run to the pblist and update memcache.
                runinfo = self.get_runinfo( user.username, game, category )
                pb['infolist'].append( runinfo )
                pb['infolist'].sort( key=itemgetter('category') )
                pb['infolist'].sort( key=itemgetter('num_runs') )
                self.update_cache_pblist( user.username, pblist )
                return

        # No run for this username, game combination.
        # So, add the run to this username's pblist and update memcache
        runinfo = self.get_runinfo( user.username, game, category )
        pblist.append( dict( game = game, 
                             game_code = game_code,
                             num_runs = 1,
                             infolist = [ runinfo ] ) )
        pblist.sort( key=itemgetter('game') )
        pblist.sort( key=itemgetter('num_runs'), reverse=True )
        self.update_cache_pblist( user.username, pblist )

    def update_pblist_delete( self, user, old_run ):
        # Update pblist with the removal to the old run
        pblist = self.get_pblist( user.username, no_refresh=True )
        if pblist is None:
            return

        for i, pb in enumerate( pblist ):
            if( pb['game'] == old_run['game'] ):
                pb['num_runs'] -= 1
                for j, info in enumerate( pb['infolist'] ):
                    if( info['category'] == old_run['category'] ):
                        runinfo = self.get_runinfo( user.username, 
                                                    old_run['game'], 
                                                    old_run['category'] )
                        if runinfo[ 'num_runs' ] > 0:
                            pb[ 'infolist' ][ j ] = runinfo
                        else:
                            # No other runs for game, category combo
                            del pb[ 'infolist' ][ j ]
                            if len( pb[ 'infolist' ] ) <= 0:
                                del pblist[ i ]
                        pb['infolist'].sort( key=itemgetter('category') )
                        pb['infolist'].sort( key=itemgetter('num_runs'),
                                             reverse=True )
                        pblist.sort( key=itemgetter('game') )
                        pblist.sort( key=itemgetter('num_runs'), 
                                     reverse=True )
                        self.update_cache_pblist( user.username, pblist )
                        return
                break
        logging.error( "Failed to correctly update pblist" )
        self.update_cache_pblist( user.username, None )

    def update_gamepage_put( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        date = params[ 'date' ]
        video = params[ 'video' ]
        is_bkt = params[ 'is_bkt' ]

        # Update gamepage in memcache
        gamepage = self.get_gamepage( game, no_refresh=True )
        if gamepage is None:
            return

        for d in gamepage:
            if d[ 'category' ] == category:
                if is_bkt:
                    # Update best known time for this category
                    d['bk_runner'] = user.username
                    d['bk_time'] = util.seconds_to_timestr( seconds )
                    d['bk_date'] = date
                    d['bk_video'] = video
                for i, runinfo in enumerate( d['infolist'] ):
                    if runinfo['username'] == user.username:
                        # User has run this category before
                        d['infolist'][i] = self.get_runinfo( user.username, 
                                                             game, category )
                        d['infolist'].sort( key=lambda x: util.get_valid_date(
                                x['pb_date'] ) )
                        d['infolist'].sort( key=itemgetter('pb_seconds') )
                        self.update_cache_gamepage( game, gamepage )
                        return
                
                # Category found, but user has not prev. run this category
                runinfo = self.get_runinfo( user.username, game, category )
                d['infolist'].append( runinfo )
                d['infolist'].sort( key=lambda x: util.get_valid_date(
                        x['pb_date'] ) )                
                d['infolist'].sort( key=itemgetter('pb_seconds') )
                gamepage.sort( key=lambda x: len(x['infolist']), reverse=True )
                self.update_cache_gamepage( game, gamepage )
                return
        
        # This is a new category for this game
        runinfo = self.get_runinfo( user.username, game, category )
        d = dict( category=category, 
                  category_code=util.get_code( category ),
                  infolist=[runinfo] )
        # Check for best known time. Since we update games.Games before 
        # updating gamepage, this will catch the case for when is_bkt is true.
        game_model = self.get_game_model( util.get_code( game ) )
        if game_model is None:
            logging.error( "Failed to update gamepage for " + game )
            self.update_cache_gamepage( game, None )
            return
        gameinfolist = json.loads( game_model.info )
        for gameinfo in gameinfolist:
            if gameinfo['category'] == category:
                d['bk_runner'] = gameinfo.get( 'bk_runner' )
                d['bk_time'] = util.seconds_to_timestr( 
                        gameinfo.get( 'bk_seconds' ) )
                d['bk_date'] = util.datestr_to_date( 
                    gameinfo.get( 'bk_datestr' ) )[ 0 ]
                d['bk_video'] = gameinfo.get( 'bk_video' )
                break
        gamepage.append( d )
        self.update_cache_gamepage( game, gamepage )

    def update_gamepage_delete( self, user, old_run ):
        # Update gamepage in memcache
        gamepage = self.get_gamepage( old_run['game'], no_refresh=True )
        if gamepage is None:
            return

        for j, d in enumerate( gamepage ):
            if d['category'] == old_run['category']:
                for i, runinfo in enumerate( d['infolist'] ):
                    if runinfo['username'] == user.username:
                        new_info = self.get_runinfo( user.username, 
                                                     old_run['game'], 
                                                     old_run['category'] )
                        if new_info['num_runs'] <= 0:
                            del d['infolist'][ i ]
                            if len( d['infolist'] ) <= 0:
                                del gamepage[ j ]
                        else:
                            d['infolist'][i] = new_info
                            d['infolist'].sort( key=itemgetter('pb_seconds') )
                            gamepage.sort( key=lambda x: len(x['infolist']),
                                           reverse=True )
                        self.update_cache_gamepage( old_run['game'], 
                                                    gamepage )
                        return
                break
        logging.error( "Failed to correctly update gamepage in memcache" )
        self.update_cache_gamepage( old_run['game'], None )

    def update_runlist_for_runner_put( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        game_code = params[ 'game_code' ]
        category = params[ 'category' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        version = params[ 'version' ]
        notes = params[ 'notes' ]
        date = params[ 'date' ]
        datetime_created = params[ 'datetime_created' ]
        run_id = params[ 'run_id' ]

        # Update runlist for runner in memcache
        runlist = self.get_runlist_for_runner( user.username, 
                                               no_refresh=True )
        if runlist is not None:
            runlist.insert( 0, dict( run_id = run_id,
                                     game = game, 
                                     game_code = game_code,
                                     category = category, 
                                     time = time,
                                     date = date, 
                                     datetime_created = datetime_created,
                                     video = video,
                                     version = version,
                                     notes = notes ) )
            runlist.sort( key=lambda x: util.get_valid_date( x['date'] ),
                          reverse=True )
            self.update_cache_runlist_for_runner( user.username, runlist )

    def update_gamelist_put( self, params ):
        game_code = params[ 'game_code' ]
        game = params[ 'game' ]

        # Update gamelist in memcache if necessary
        gamelist = self.get_gamelist( no_refresh=True )
        if gamelist is not None:
            found_game = False
            for gamedict in gamelist:
                if( gamedict['game_code'] == game_code ):
                    found_game = True
                    gamedict['num_pbs'] += 1
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

    def update_gamelist_delete( self, old_run ):
        # Fix the gamelist with the removal of the old run
        gamelist = self.get_gamelist( no_refresh=True )
        if gamelist is not None:
            for i, gamedict in enumerate( gamelist ):
                if( gamedict[ 'game' ] == old_run[ 'game' ] ):
                    gamedict['num_pbs'] -= 1
                    if gamedict['num_pbs'] <= 0:
                        del gamelist[ i ]
                    gamelist.sort( key=itemgetter('num_pbs'), 
                                   reverse=True )
                    self.update_cache_gamelist( gamelist )
                    break

    def update_runnerlist_put( self, params ):
        user = params[ 'user' ]

        # Update runnerlist in memcache if necessary
        runnerlist = self.get_runnerlist( no_refresh=True )
        if runnerlist is not None:
            found_runner = False
            for runnerdict in runnerlist:
                if( runnerdict['username'] == user.username ):
                    found_runner = True
                    runnerdict['num_pbs'] += 1
                    runnerlist.sort( key=itemgetter('username') )
                    runnerlist.sort( key=itemgetter('num_pbs'), 
                                     reverse=True )
                    self.update_cache_runnerlist( runnerlist )
                    break
            if not found_runner:
                logging.error( "Failed to find " + user.username 
                               + " in runnerlist" )

    def update_runnerlist_delete( self, user ):
        # Fix the runnerlist with the removal of the old run
        runnerlist = self.get_runnerlist( no_refresh=True )
        if runnerlist is not None:
            for runnerdict in runnerlist:
                if( runnerdict['username'] == user.username ):
                    runnerdict['num_pbs'] -= 1
                    runnerlist.sort( key=itemgetter('username') )
                    runnerlist.sort( key=itemgetter('num_pbs'), 
                                     reverse=True )
                    self.update_cache_runnerlist( runnerlist )
                    break

    def update_user_has_run_delete( self, user, old_run ):
        # This refresh is so cheap, let's just kill the old value
        self.update_cache_user_has_run( user.username, old_run['game'], None )

    # Returns True if putting new run succeeded, False otherwise
    def put_new_run( self, params ):
        user = params.get( 'user' )
        game = params.get( 'game' )
        category = params.get( 'category' )
        seconds = params.get( 'seconds' )
        time = params.get( 'time' )
        video = params.get( 'video' )
        version = params.get( 'version' )
        notes = params.get( 'notes' )
        valid = params.get( 'valid' )

        # Add a new run to the database
        try:
            new_run = runs.Runs( username = user.username,
                                 game = game,
                                 category = category,
                                 seconds = seconds,
                                 date = params[ 'date' ],
                                 version = version,
                                 notes = notes,
                                 parent = runs.key() )
            try:
                if video:
                    new_run.video = video
            except db.BadValueError:
                params[ 'video_error' ] = "Invalid video URL"
                valid = False
        except db.BadValueError:
            valid = False
        
        if not valid:
            return False

        new_run.put( )
        params[ 'run_id' ] = str( new_run.key().id() )
        params[ 'datetime_created' ] = new_run.datetime_created
        logging.debug( "Put new run for runner " + user.username
                       + ", game = " + game + ", category = " + category 
                       + ", time = " + time )

        # Check whether this is the first run for this username, game,
        # category combination.  This will determine whether we need to update
        # the gamelist and runnerlist, as well as update the num_pbs
        # for the game and runner.
        delta_num_pbs = 0
        num_runs = self.num_runs( user.username, game, category, 2 )
        if num_runs == 1:
            delta_num_pbs = 1

        # Update games.Games, runners.Runners
        self.update_runner( user, delta_num_pbs )
        self.update_games_put( params, delta_num_pbs )

        # Update memcache
        self.update_cache_run_by_id( new_run.key().id(), new_run )
        # Must update runinfo before updating pblist, gamepage since these 
        # both rely on runinfo being up to date
        self.update_runinfo_put( params )
        self.update_pblist_put( params )
        self.update_gamepage_put( params )
        self.update_runlist_for_runner_put( params )
        self.update_cache_user_has_run( user.username, game, True )
        self.update_cache_last_run( user.username, new_run )
                     
        if num_runs <= 0:
            logging.error( "Unexpected count [" + str(count) 
                           + "] for number of runs for "
                           + username + ", " + game + ", " + category )
            self.update_cache_gamelist( None )
            self.update_cache_runnerlist( None )
        if delta_num_pbs == 1:
            self.update_gamelist_put( params )
            self.update_runnerlist_put( params )

        return True

    # Returns True on success, False otherwise
    def put_existing_run( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        game_code = params[ 'game_code' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        version = params[ 'version' ]
        notes = params[ 'notes' ]
        valid = params[ 'valid' ]
        run_id = params[ 'run_id' ]

        # Grab the old run, which we will update to be the new run
        new_run = self.get_run_by_id( run_id )
        if new_run is None or new_run.username != user.username:
            return False

        # Store the contents of the old run
        old_run = dict( game = new_run.game,
                        category = new_run.category,
                        seconds = new_run.seconds )

        # Update the run
        try:
            new_run.game = game
            new_run.category = category
            new_run.seconds = seconds
            new_run.date = params['date']
            new_run.version = version
            new_run.notes = notes
        except db.BadValueError:
            valid = False
        if video:
            try:
                new_run.video = video
            except db.BadValueError:
                params['video_error'] = "Invalid video URL"
                valid = False
        elif new_run.video:
            new_run.video = None
            
        if not valid:
            return False
            
        new_run.put( )
        logging.debug( "Put updated run for runner " + user.username
                       + ", game = " + game + ", category = " + category
                       + ", time= " + time + ", run_id = " + run_id )

        # Figure out the change in num_pbs for the old and new game, as well
        # as the runner
        delta_num_pbs_old = 0
        delta_num_pbs_new = 0
        if game != old_run['game'] or category != old_run['category']:
            num_runs = self.num_runs( user.username, old_run[ 'game' ], 
                                      old_run[ 'category' ], 1 )
            if num_runs == 0:
                delta_num_pbs_old = -1
            num_runs = self.num_runs( user.username, game, category, 2 )
            if num_runs == 1:
                delta_num_pbs_new = 1
            
        # Update games.Games and runners.Runners
        self.update_runner( user, delta_num_pbs_old + delta_num_pbs_new )
        if game == old_run['game']:
            self.update_games_delete( params['game_model'], delta_num_pbs_old )
        else:
            self.update_games_delete( self.get_game_model( util.get_code( 
                        old_run['game'] ) ), delta_num_pbs_old )
        self.update_games_put( params, delta_num_pbs_new )

        # Update memcache with the removal of the old run and addition of the
        # new run.
        self.update_cache_run_by_id( run_id, new_run )
        # Must update runinfo before pblist and gamepage as in put_new_run()
        self.update_runinfo_delete( user, old_run )
        self.update_runinfo_put( params )
        self.update_pblist_delete( user, old_run )
        self.update_pblist_put( params )
        self.update_gamepage_delete( user, old_run )
        self.update_gamepage_put( params )
        self.update_user_has_run_delete( user, old_run )
        self.update_cache_user_has_run( user.username, game, True )

        # Update gamelist and runnerlist in memcache
        if delta_num_pbs_old == -1:
            self.update_gamelist_delete( old_run )
            self.update_runnerlist_delete( user )
        if delta_num_pbs_new == 1:
            self.update_gamelist_put( params )
            self.update_runnerlist_put( params )

        # Replace the old run in the runlist for runner in memcache
        runlist = self.get_runlist_for_runner( user.username, no_refresh=True )
        if runlist:
            for run in runlist:
                if run[ 'run_id' ] == run_id:
                    run[ 'game' ] = game
                    run[ 'game_code' ] = game_code
                    run[ 'category' ] = category
                    run[ 'time' ] = time
                    run[ 'date' ] = new_run.date
                    run[ 'video' ] = video
                    run[ 'version' ] = version
                    run[ 'notes' ] = notes
                    runlist.sort( key=lambda x: util.get_valid_date( 
                        x['date'] ), reverse=True )
                    self.update_cache_runlist_for_runner( user.username, 
                                                          runlist )
                    break

        # Check to see if we need to replace the last run for this user
        last_run = self.get_last_run( user.username, no_refresh=True )
        if( last_run is not None 
            and new_run.key().id() == last_run.key().id() ):
            self.update_cache_last_run( user.username, new_run )

        return True
