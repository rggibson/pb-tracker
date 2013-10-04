from google.appengine.ext import db

def key( name = 'default' ):
    return db.Key.from_path( 'games', name )    

# info is a list of dictionaries, stored as json, where the dictionary keys
# are 'category', 'bk_runner', 'bk_seconds', 'bk_video'
class Games( db.Model ):
    game = db.StringProperty( required=True )
    info = db.TextProperty( required=True ) 
