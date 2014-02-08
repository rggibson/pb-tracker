# games.py
# Author: Richard Gibson
#
# Stores game, category and best known time information.  Categories and best 
# known times are stored as JSON text with the following keys: `category`, 
# `bk_runner`, `bk_seconds`, `bk_datestr`, `bk_video` and `bk_updater` 
# (hidden field).  The date of the best known run, `bk_datestr`, is stored as 
# a 'mm/dd/yyyy' string and is converted to a Python `Date` object with 
# `util.datestr_to_date` when required.  Finally, `games.py` also stores the 
# number of pbs tracked for each game.  This is an optimization measure as 
# the query required to calculate this number is expensive.
#
# Games is a superset of the games and categories submitted by users and 
# stored in runs.py.  
# When PB Tracker originally launched, many Games entities were created to 
# provide an opening database of games and categories to suggest to runners 
# on the submit page.  Any game and/or category submitted that is not in the 
# database is immediately added. Games entities are currently never deleted.
#
import re

from google.appengine.ext import db

def key( name = 'default' ):
    return db.Key.from_path( 'games', name )    

GAME_CATEGORY_RE = re.compile( r"^[a-zA-Z0-9 +=,.:!@#$%&*()'/\\-]{1,100}$" )
def valid_game_or_category( game_or_category ):
    return GAME_CATEGORY_RE.match( game_or_category )

# info is a list of dictionaries, stored as json, where the dictionary keys
# are 'category', 'bk_runner', 'bk_seconds', 'bk_video'
class Games( db.Model ):
    game = db.StringProperty( required=True )
    info = db.TextProperty( required=True ) 
    num_pbs = db.IntegerProperty( default=0 )
