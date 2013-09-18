import hmac
import hashlib
import random
from string import letters

SECRET = 'redred11'

# Hashing utility functions
def hash_str(s):
    return hmac.new(SECRET, s).hexdigest()
    
def make_secure_val(s):
    return "{0}|{1}".format(s, hash_str(s))

def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val

# Hasing functions with salt
def make_salt():
    return ''.join(random.choice(letters) for x in xrange(5))
        
def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return "{0}|{1}".format(h, salt)

def valid_pw(name, pw, h):
    parts = h.split('|')
    if len(parts) > 1:
        return h == make_pw_hash(name, pw, parts[1])

# Time string utility functions
def seconds_to_timestr( seconds ):
    secs = seconds
    mins = secs / 60
    secs = secs % 60
    hours = mins / 60
    mins = mins % 60

    if( hours > 0 ):
        timestr = str(hours) + ':' + str(mins) + ':' + str(secs)
    elif( mins > 0 ):
        timestr = str(mins) + ':' + str(secs)
    else:
        timestr = '00:' + str(secs)

    return timestr
