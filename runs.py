from google.appengine.ext import db
from datetime import date

def key( name = 'default' ):
    return db.Key.from_path( 'runs', name )    

class Runs( db.Model ):
    username = db.StringProperty( required = True )
    game = db.StringProperty( required = True )
    category = db.StringProperty( required = True )
    seconds = db.IntegerProperty( required = True )
    date = db.DateProperty( default = date( 2013, 01, 01 ) )
    datetime_created = db.DateTimeProperty( auto_now_add = True )
    version = db.StringProperty( required = False )
    video = db.LinkProperty( required = False )
