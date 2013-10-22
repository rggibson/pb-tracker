import hmac
import hashlib
import random
from string import letters
import logging
import re
import secret

# Hashing utility functions
def hash_str(s):
    return hmac.new(secret.SECRET, s).hexdigest()
    
def make_secure_val(s):
    return "{0}|{1}".format( s, hash_str(s) )

def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val( val ):
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

# Game, time string utility functions
def get_code( string ):
    # First, remove apostrophes
    res = re.sub( "'", "", string )
    # Then, substitute consecutive nonalphanumeric characters with a dash, with
    # the exception of plusses (NG+ is a legit category).
    # Also, convert to lower case
    res = re.sub( '[^a-zA-Z0-9+]+', '-', res ).lower()
    # We must use the percent encoding for the plus sign because it breaks
    # query strings
    res = re.sub( '\+', '%2B', res )
    # Finally, remove leading and trailing dashes
    res = re.sub( '^-', '', res )
    res = re.sub( '-$', '', res )
    return res

def seconds_to_timestr( seconds ):
    if seconds is None:
        return None

    secs = int( round( seconds ) )
    mins = secs / 60
    secs = secs % 60
    hours = mins / 60
    mins = mins % 60

    hours_str = ''
    if( hours > 0 ):
        hours_str = str(hours) + ':'
    mins_str = str(mins) + ':'
    if( mins < 10 and hours > 0 ):
        mins_str = "0" + mins_str
    secs_str = str(secs)
    if( secs < 10 ):
        secs_str = "0" + secs_str

    return hours_str + mins_str + secs_str

def timestr_to_seconds( time ):
    parts = time.split(':')

    if( len( parts ) > 3 ):
        return (None, "too many colons")

    try:
        seconds = int( parts[ -1 ] )
    except ValueError:
        return (None, "bad seconds value [" + parts[ -1 ] + "]")
    if( seconds < 0 or seconds >= 60 ):
        return (None, "seconds must be between 00 and 59")
    if( len( parts ) > 1 ):
        try:
            mins = int( parts[ -2 ] )
        except ValueError:
            return (None, "bad minutes value [" + parts[ -2 ] + "]")
        if( mins < 0 or mins >= 60 ):
            return (None, "minutes must be between 00 and 59")
        seconds += 60 * mins
        if( len( parts ) > 2 ):
            try:
                hours = int( parts[ 0 ] )
            except ValueError:
                return (None, "bad hours value [" + parts[ 0 ] + "]")
            if( hours < 0 ):
                return (None, "hours must be nonnegative")
            seconds += 3600 * hours

    return (seconds, "")

# Gravatar utility function
def get_gravatar_url( gravatar, size=80 ):
    if gravatar:
        return ( 'http://www.gravatar.com/avatar/' + gravatar + "?s=" 
                 + str( size ) )
    else:
        return ''
