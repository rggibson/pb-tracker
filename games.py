from google.appengine.ext import db

def key(name = 'default'):
    return db.Key.from_path('games', name)    

class Games(db.Model):
    game = db.StringProperty(required = True)
    categories = db.ListProperty(str, required = True)
