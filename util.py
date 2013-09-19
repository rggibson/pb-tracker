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

# Game, time string utility functions
def get_game_or_category_code( game_or_category ):
    # Substitute all sets of consecutive nonalphanumeric characters with a dash
    return re.sub( '[^a-zA-Z0-9]+', '-', game_or_category ).lower()

def seconds_to_timestr( seconds ):
    secs = seconds
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
