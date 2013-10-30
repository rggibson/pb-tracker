# runs.py
# Author: Richard Gibson
#
# Stores submitted runs.  Run times are stored in seconds and converted to 
# hh:mm:ss with util.seconds_to_timestr when required.

from google.appengine.ext import db
from datetime import date

def key( name = 'default' ):
    return db.Key.from_path( 'runs', name )    

class Runs( db.Model ):
    username = db.StringProperty( required = True )
    game = db.StringProperty( required = True )
    category = db.StringProperty( required = True )
    seconds = db.IntegerProperty( required = True )
    date = db.DateProperty( required = False )
    datetime_created = db.DateTimeProperty( required = True, 
                                            auto_now_add = True )
    version = db.StringProperty( required = False )
    video = db.LinkProperty( required = False )
    notes = db.TextProperty( required = False )
