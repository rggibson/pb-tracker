import util
import logging
import games
import json
import handler

class UpdateBkt( handler.Handler ):
    def get( self, game_code ):
        user = self.get_user( )

        # Get the category
        category_code = self.request.get( 'c' )
        if user is None or category_code is None:
            self.error( 404 )
            self.render( "404.html" )
            return
        
        # Check to make sure that the user has run this game
        game_model = self.get_game_model( game_code )
        user_has_run = self.get_user_has_run( user.username, game_model.game )
        if not user_has_run:
            self.error( 404 )
            self.render( "404.html" )
            return

        # Find the corresponding gameinfo for this category
        gameinfolist = json.loads( game_model.info )
        gameinfo = None
        for g in gameinfolist:
            if util.get_code( g['category'] ) == category_code:
                gameinfo = g
                break
        if gameinfo is None:
            self.error( 404 )
            self.render( "404.html" )
            return

        params = dict( user=user, game=game_model.game, 
                       category=gameinfo['category'] )
        try:
            params['username'] = gameinfo['bk_runner']
            params['time'] = util.seconds_to_timestr( gameinfo['bk_seconds'] )
            params['video'] = gameinfo['bk_video']
            params['updating'] = True
        except KeyError:
            params['username'] = ''
            params['time'] = ''
            params['video'] = ''
            params['updating'] = False

        return_url = self.get_return_url( )
        if return_url[ 0 : len( '/runner/' ) ] == '/runner/':
            params['from_runnerpage'] = True
        else:
            params['from_runnerpage'] = False
            
        self.render( "updatebkt.html", **params )

    def post( self, game_code ):
        user = self.get_user( )

        # Get the category
        category_code = self.request.get( 'c' )
        if user is None or category_code is None:
            self.error( 404 )
            self.render( "404.html" )
            return
        
        # Check to make sure that the user has run this game
        game_model = self.get_game_model( game_code )
        user_has_run = self.get_user_has_run( user.username, game_model.game )
        if not user_has_run:
            self.error( 404 )
            self.render( "404.html" )
            return

        # Find the corresponding gameinfo for this category
        gameinfolist = json.loads( game_model.info )
        gameinfo = None
        for g in gameinfolist:
            if util.get_code( g['category'] ) == category_code:
                gameinfo = g
                break
        if gameinfo is None:
            self.error( 404 )
            self.render( "404.html" )
            return

        # Get the inputs
        username = self.request.get( 'username' )
        time = self.request.get( 'time' )
        video = self.request.get( 'video' )

        params = dict( user=user, game=game_model.game, 
                       category=gameinfo['category'], username=username,
                       time=time, video=video )

        # Check for where we came from
        return_url = self.get_return_url( )
        if return_url[ 0 : len( '/runner/' ) ] == '/runner/':
            params['from_runnerpage'] = True
        else:
            params['from_runnerpage'] = False

        # Make sure we got a username
        if not username:
            params['username_error'] = "You must enter a runner"
            self.render( "updatebkt.html", **params )
            return

        # Parse the time into seconds, ensure it is valid
        ( seconds, time_error ) = util.timestr_to_seconds( time )
        if not seconds:
            params['time_error'] = "Invalid time: " + time_error
            self.render( "updatebkt.html", **params )
            return
        time = util.seconds_to_timestr( seconds ) # Enforce standard format
        params['time'] = time

        # Store the best known time
        gameinfo['bk_runner'] = username
        gameinfo['bk_seconds'] = seconds
        gameinfo['bk_video'] = video
        gameinfo['bk_updater'] = user.username
        game_model.info = json.dumps( gameinfolist )
        game_model.put( )

        # Update game_model in memcache
        self.update_cache_game_model( game_code, game_model )

        # Update gamepage in memcache
        gamepage = self.get_gamepage( game_model.game, no_refresh=True )
        if gamepage is not None:
            for d in gamepage:
                if d['category'] == gameinfo['category']:
                    d['bk_runner'] = username
                    d['bk_time'] = time
                    d['bk_video'] = video
                    break
            self.update_cache_gamepage( game_model.game, gamepage )

        # All dun
        self.goto_return_url( )
