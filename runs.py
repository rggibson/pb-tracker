from google.appengine.ext import db

def key(name = 'default'):
    return db.Key.from_path('runs', name)    

class Runs(db.Model):
    username = db.StringProperty(required = True)
    game = db.StringProperty(required = True)
    category = db.StringProperty(required = True)
    seconds = db.IntegerProperty(required = True)
    datetime_created = db.DateTimeProperty(auto_now_add = True)
    console = db.StringProperty(required = False)
    version = db.StringProperty(required = False)
    region = db.StringProperty(required = False)
    video = db.LinkProperty(required = False)
