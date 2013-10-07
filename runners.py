from google.appengine.ext import db

def key( name = 'default' ):
    return db.Key.from_path( 'runners', name )    

class Runners( db.Model ):
    username = db.StringProperty( required = True )
    password = db.StringProperty( required = True )
    twitter = db.StringProperty( required = False )
    youtube = db.StringProperty( required = False )
    twitch = db.StringProperty( required = False )
    gravatar = db.StringProperty( required = False )
    datetime_created = db.DateTimeProperty( auto_now_add = True )
