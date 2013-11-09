# runners.py
# Author: Richard Gibson
#
# Stores runner (user) info.  Passwords are stored encrypted with sha256 and 
# salt (see util.make_pw_hash), while Gravatar emails are also stored 
# encrypted with md5 as needed for Gravatar usage.  Visible columns is a 
# dictionary of booleans, stored in JSON, that determine which columns are
# visible on the runner's default page.  Finally, similar to games.py, Runners
# also stores the number of pbs tracked for each runner.  This is an 
# optimization measure as the query required to calculate this number is
# expensive.
#
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
    visible_columns = db.TextProperty( required = False )
    num_pbs = db.IntegerProperty( default = 0 )
    timezone = db.TextProperty( required = False ) # Only used for asup
    is_mod = db.BooleanProperty( default = False )
