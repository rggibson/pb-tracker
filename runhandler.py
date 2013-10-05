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

    def update_games( self, params ):
        game_model = params[ 'game_model' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        game_code = params[ 'game_code' ]
        category_found = params[ 'category_found' ]

        if game_model is None:
            # Add a new game to the database
            info = [ dict( category=category ) ]
            game_model = games.Games( game = game,
                                      info = json.dumps( info ),
                                      parent = games.key(),
                                      key_name = game_code )
            game_model.put( )
            logging.warning( "Put new game " + game + " with "
                             + " category " + category + " in database." )
            self.update_cache_game_model( game_code, game_model )
        elif not category_found:
            # Add a new category for this game in the database
            info = json.loads( game_model.info )
            info.append( dict( category=category ) )
            game_model.info = json.dumps( info )
            game_model.put( )
            logging.debug( "Added category " + category + " to game " 
                           + game + " in database." )

    def update_runinfo_put( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        category = params[ 'category' ]
        seconds = params[ 'seconds' ]
        time = params[ 'time' ]
        video = params[ 'video' ]

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
            runinfo['video'] = video
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
                q = db.Query( runs.Runs, projection=('seconds', 'video') )
                q.ancestor( runs.key() )
                q.filter( 'username =', user.username )
                q.filter( 'game =', old_run['game'] )
                q.filter( 'category =', old_run['category'] )
                q.order( 'seconds' )
                q.order( 'datetime_created' )
                pb_run = q.get( )
                if pb_run:
                    runinfo['pb_seconds'] = pb_run.seconds
                    runinfo['pb_time'] = util.seconds_to_timestr( 
                        pb_run.seconds )
                    runinfo['video'] = pb_run.video
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
                                             pb_seconds=None,
                                             pb_time=None,
                                             num_runs=0,
                                             avg_seconds=0,
                                             avg_time='00:00',
                                             video=None ) )

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
                for i, info in enumerate( pb['infolist'] ):
                    if( info['category'] == category ):
                        pb['infolist'][i] = self.get_runinfo( user.username, 
                                                              game, category )
                        pb['infolist'].sort( key=itemgetter('num_runs'),
                                             reverse=True )
                        self.update_cache_pblist( user.username, pblist )
                        return

                # User has run this game, but not this category.
                # Add the run to the pblist and update memcache.
                runinfo = self.get_runinfo( user.username, game, category )
                pb['infolist'].append( runinfo )
                self.update_cache_pblist( user.username, pblist )
                return

        # No run for this username, game combination.
        # So, add the run to this username's pblist and update memcache
        runinfo = self.get_runinfo( user.username, game, category )
        pblist.append( dict( game = game, 
                             game_code = game_code,
                             infolist = [ runinfo ] ) )
        pblist.sort( key=itemgetter('game') )
        self.update_cache_pblist( user.username, pblist )

    def update_pblist_delete( self, user, old_run ):
        # Update pblist with the removal to the old run
        pblist = self.get_pblist( user.username, no_refresh=True )
        if pblist is None:
            return

        for i, pb in enumerate( pblist ):
            if( pb['game'] == old_run['game'] ):
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
                        pb['infolist'].sort( key=itemgetter('num_runs'),
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
        video = params[ 'video' ]

        # Update gamepage in memcache
        gamepage = self.get_gamepage( game, no_refresh=True )
        if gamepage is None:
            return

        for d in gamepage:
            if d[ 'category' ] == category:
                for i, runinfo in enumerate( d['infolist'] ):
                    if runinfo['username'] == user.username:
                        d['infolist'][i] = self.get_runinfo( user.username, 
                                                             game, category )
                        d['infolist'].sort( key=itemgetter('pb_seconds') )
                        self.update_cache_gamepage( game, gamepage )
                        return
                
                # Category found, but user has not prev. run this category
                runinfo = self.get_runinfo( user.username, game, category )
                d['infolist'].append( runinfo )
                d['infolist'].sort( key=itemgetter('pb_seconds') )
                gamepage.sort( key=lambda x: len(x['infolist']), reverse=True )
                self.update_cache_gamepage( game, gamepage )
                return
        
        # This is a new category for this game
        runinfo = self.get_runinfo( user.username, game, category )
        d = dict( category=category, 
                  category_code=util.get_code( category ),
                  infolist=[runinfo] )
        # Check for best known time
        game_model = self.get_game_model( util.get_code( game ) )
        if game_model is None:
            logging.error( "Failed to update gamepage for " + game )
            self.update_cache_gamepage( game, None )
            return
        gameinfolist = json.loads( game_model.info )
        for gameinfo in gameinfolist:
            if gameinfo['category'] == category:
                try:
                    d['bk_runner'] = gameinfo['bk_runner']
                    d['bk_time'] = util.seconds_to_timestr( 
                        gameinfo['bk_seconds'] )
                    d['bk_video'] = gameinfo['bk_video']
                except KeyError:
                    d['bk_runner'] = None
                    d['bk_time'] = None
                    d['bk_video'] = None
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
        self.udpate_cache_gamepage( old_run['game'], None )

    def update_runlist_for_runner_put( self, params ):
        user = params[ 'user' ]
        game = params[ 'game' ]
        game_code = params[ 'game_code' ]
        category = params[ 'category' ]
        time = params[ 'time' ]
        video = params[ 'video' ]
        datetime_created = params[ 'datetime_created' ]
        run_id = params[ 'run_id' ]

        # Update runlist for runner in memcache
        runlist = self.get_runlist_for_runner( user.username, 
                                               no_refresh=True )
        if runlist is not None:
            runlist.insert( 0, dict( run_id = run_id,
                                     game = game, game_code = game_code,
                                     category = category, time = time, 
                                     date = datetime_created.strftime(
                                         "%a %b %d %H:%M:%S %Y" ),
                                     video = video ) )
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
                    # We may have a stale number for pbs, so recount
                    q = db.Query( runs.Runs, 
                                  projection=('username', 'category'),
                                  distinct=True )
                    q.ancestor( runs.key() )
                    q.filter( 'game =', game )
                    num_pbs = q.count( limit=1000 )
                    gamedict['num_pbs'] = num_pbs
                    gamelist.sort( key=itemgetter('game_code') )
                    gamelist.sort( key=itemgetter('num_pbs'), 
                                   reverse=True )
                    self.update_cache_gamelist( gamelist )
                    break
            if not found_game:
                # This game wasn't found in the gamelist, so add it
                gamelist.append( dict( game = game, game_code = game_code,
                                       num_pbs = 1 ) )
                gamelist.sort( key=itemgetter('game_code') )
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
                    gamelist.sort( key=itemgetter('game_code') )
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
                    # Memcache could be stale, so recalculate num_pbs
                    q = db.Query( runs.Runs, 
                                  projection=('game', 'category'),
                                  distinct = True )
                    q.ancestor( runs.key() )
                    q.filter( 'username =', user.username )
                    num_pbs = q.count( limit=1000 )
                    runnerdict['num_pbs'] = num_pbs
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
