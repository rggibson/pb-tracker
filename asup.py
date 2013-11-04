# asup.py
# Author: Richard Gibson
#
# Handler for communication between PB Tracker and an external source, like a
# splits program.  Follows the protocol currently listed here:
# https://docs.google.com/document/d/13UAc4CQTSMBAiEHm7xNdJYT8v27VZY1GJc2aYsaFVu0/edit#
#

import handler
import json
import util

class Asup( handler.Handler ):
    def get( self ):
        # By default, return success, a link to the handler, and a link to
        # the protocol doc
        d = dict( type="success",
                  link="http://www.pbtracker.net/asup",
                  spec=( "https://docs.google.com/document/d/"
                         + "13UAc4CQTSMBAiEHm7xNdJYT8v27VZY1GJc2aYsaFVu0/"
                         + "edit#" ) )
        self.render_json( d )

    def post( self ):
        # Fetch the posted data
        body_json = self.request.body        
        body = json.loads( body_json )
        body_type = body.get( 'type' )

        # Currently 5 types: verifylogin, gamelist, categories, gamecategories
        # and submitrun
        response = dict( result="success" )
        if body_type is None:
            response['result'] = "fail"
            response['message'] = "No type given."
        
        elif body_type == 'verifylogin':
            username = body.get( 'username' )
            password = body.get( 'password' )
            if username is None:
                response['result'] = 'fail'
                response['message'] = 'No username specified.'
            elif password is None:
                response['result'] = 'fail'
                response['message'] = 'No password specified.'
            else:
                ( valid, errors ) = self.verify_login( username, password )
                if not valid:
                    response['result'] = 'fail'
                    response['message'] = ''
                    for error_type, error in errors.iteritems( ):
                        response['message'] += error + ' '

        elif body_type == 'gamelist':
            # Note that this is a different type of gamelist than the one
            # generated in games.py
            categories = self.get_categories( )
            d = dict( )
            for game in categories.keys( ):
                d[ util.get_code( game ) ] = game
            response['data'] = d

        elif body_type == 'categories':
            categories = self.get_categories( )
            d = dict( )
            for game, categorylist in categories.iteritems( ):
                game_code = util.get_code( game )
                for category in categorylist:
                    category_code = util.get_code( category )
                    d[ game_code + ':' + category_code ] = ( game + ' - ' 
                                                             + category )
            response['data'] = d

        elif body_type == 'gamecategories':
            game_code = body.get( 'game' )
            game_model = self.get_game_model( game_code )
            if game_code is None:
                response['result'] = 'fail'
                response['message'] = 'No game specified.'
            elif game_model is None:
                response['result'] = 'fail'
                response['message'] = 'Unknown game [' + game_code + '].'
            else:
                d = dict( )
                gameinfolist = json.loads( game_model.info )
                for gameinfo in gameinfolist:
                    category = gameinfo['category']
                    d[ util.get_code( category ) ] = category
                response['data'] = d
        
        else:
            response['result'] = 'fail'
            response['message'] = "Unknown type [" + body_type + "]."

        # All dun
        self.render_json( response )
