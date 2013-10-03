import games
import util
import handler

class FixerUpper( handler.Handler ):
    def get( self ):
        # Make sure it's me
        user = self.get_user( )
        if not user or user.username != "rggibson":
            self.error( 404 )
            self.render( "404.html", user=user )
            return

        self.write( "FixerUpper in progress... " )

        # Create the list of games
        gamelist = [ dict( game='Mega Man 2', 
                           categories=[ 'Any% (Normal)',
                                        'Any% (Normal) no zips',
                                        'Any% (Difficult)',
                                        'Any% (Difficult) no zips' ] ),
                     dict( game='Rockman 2',
                           categories=[ 'Any%',
                                        'Any% no zips' ] ),
                     dict( game='Mega Man 3',
                           categories=[ 'Any%',
                                        '8 Robot Masters',
                                        '16 Robot Masters',
                                        '8 Robot Masters (buster only)' ] ),
                     dict( game='Beavis and Butt-head',
                           categories=[ 'Any%',
                                        '100%' ] ) ]

        # Add the games, overwriting any existing versions in database
        for g in gamelist:
            game_code = util.get_code( g['game'] )
            game_model = games.Games( game=g['game'],
                                      categories=g['categories'],
                                      key_name=game_code,
                                      parent=games.key() )
            game_model.put( )
            self.update_cache_game_model( game_code, game_model )

        self.write( "FixerUpper complete!" )
