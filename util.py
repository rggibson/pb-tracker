# util.py
# Author: Richard Gibson
#
# A collection of useful functions that perform a variety of helpful things,
# including secure cookie generation, password hashing / validation, time and
# date conversions, and string coding. 
#

import hmac
import hashlib
import random
from string import letters
import logging
import re
import secret

from datetime import date
from datetime import timedelta

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

# Date utility functions
def get_valid_date( d ):
    if d is not None:
        return d
    else:
        return date( 1970, 1, 1 )

def datestr_to_date( datestr ):
    if datestr is None or len( datestr ) <= 0:
        return ( None, '' )

    parts = datestr.split( '/' )
    if len( parts ) != 3:
        return ( None, "format should be mm/dd/yyyy" )

    # strftime breaks with dates before 1900, but JayFermont suggested
    # they break before 1970, so let's disallow anything before 1970.
    # To help users out, let's change two-digit dates to the 1900/2000
    # equivalent.
    year = int( parts[ 2 ] )
    if year >= 0 and year <= 69:
        year += 2000
    elif year >= 70 and year < 100:
        year += 1900
    try:
        d = date( year, int( parts[ 0 ] ), int( parts[ 1 ] ) )
        # Add a day to today to account for timezone problems
        if d > date.today( ) + timedelta( days=1 ): 
            return ( None, "that date is in the future!" )
        elif year < 1970:
            return ( None, "date must be after Dec 31 1969" )
    except ValueError:
        return ( None, 'that day is not on our calendar' )

    return ( d, '' )

# Function for getting the default visible columns on PB page
def get_default_visible_columns( ):
    return dict( boxart=True,
                 game=True,
                 category=True,
                 pb=True,
                 date=True,
                 version=False,
                 runs=True,
                 avg_time=True,
                 bkt=True )
