# signup.py
# Author: Richard Gibson
#
# Handles user registration and creates runners.Runners entities.  Upon 
# successful signup, the user is redirected to his or her previous page
# stored in the 'from' query parameter.
#

import handler
import runners
import re
import util
import hashlib
import json

from pytz.gae import pytz

USER_RE = re.compile( r"^[a-zA-Z0-9_-]{1,20}$" )
def valid_username( username ):
    return USER_RE.match( username )

PASS_RE = re.compile( r"^.{3,20}$" )
def valid_password( password ):
    return PASS_RE.match( password )

EMAIL_RE = re.compile( r"^[\S]+@[\S]+\.[\S]+$" )
def valid_email( email ):
    return EMAIL_RE.match( email )


class Signup( handler.Handler ):
    def get( self ):
        user = self.get_user( )
        return_url = self.request.get( 'from' )
        if not return_url:
            return_url = "/"
        elif user is not None and user.is_mod:
            # Mod is editing a user's profile, possibly his or her own
            username_code = return_url.split( '/' )[ -1 ]
            user = self.get_runner( username_code )
            
        if user is not None:
            # Editing profile
            params = dict( user=user,
                           youtube=user.youtube,
                           twitch=user.twitch,
                           return_url=return_url )
            if user.twitter:
                params['twitter'] = '@' + user.twitter
            if user.gravatar:
                params['gravatar'] = '<private email>'
                params['gravatar_url'] = util.get_gravatar_url( user.gravatar,
                                                                30 )
            if user.timezone is not None:
                params['timezone'] = user.timezone
            self.render( "signup.html", timezones=pytz.common_timezones,
                         **params )
        else:
            # New user
            self.render( "signup.html", return_url=return_url,
                         timezones=pytz.common_timezones )

    def post( self ):
        user = self.get_user( )
        username = self.request.get( 'username' )
        password = self.request.get( 'password' )
        verify = self.request.get( 'verify' )
        twitter = self.request.get( 'twitter' )
        if twitter[ 0:1 ] == '@':
            twitter = twitter[ 1: ]
        youtube = self.request.get( 'youtube' )
        youtube = youtube.split( '/' )[ -1 ]
        twitch = self.request.get( 'twitch' )
        twitch = twitch.split( '/' )[ -1 ]
        timezone = self.request.get( 'timezone' )
        gravatar = self.request.get( 'gravatar' )
        if user is not None:
            username_code = util.get_code( user.username )
        else:
            username_code = util.get_code( username )
        return_url = self.request.get( 'from' )
        if not return_url:
            return_url = "/"
        elif user is not None and user.is_mod:
            # Mod is editing a user's profile, possibly his or her own
            username_code = return_url.split( '/' )[ -1 ]
            user = self.get_runner( username_code )

        params = dict( user = user,
                       username = username,
                       password = password,
                       verify = verify,
                       twitter = twitter,
                       youtube = youtube,
                       twitch = twitch,
                       gravatar = gravatar,
                       timezone = timezone,
                       return_url = return_url )

        valid = True

        if user is None and not valid_username( username ):
            params['user_error'] = ( "Username must be between " 
                                     + "1 and 20 alphanumeric, dash, or "
                                     + "underscore characters." )
            valid = False
        elif user is None:
            # Check if username already exists
            runner = self.get_runner( username_code )
            if runner is not None:
                params['user_error'] = "That user already exists."
                valid = False
        
        if not valid_password( password ):
            if user is None or len( password ) > 0:
                params['pass_error'] = ( "Password must be between "
                                         + "3 and 20 characters." )
                valid = False

        if password != verify:
            params['ver_error'] = "Passwords do not match."
            valid = False

        if gravatar != "" and not valid_email( gravatar ):
            if( user is None or not user.gravatar 
                or gravatar != '<private email>' ):
                params['gravatar_error'] = "That's not a valid email."
                valid = False
        if user is not None and gravatar == '<private email>':
            params['gravatar_url'] = util.get_gravatar_url( user.gravatar,
                                                            30 )

        if timezone != '' and timezone not in pytz.common_timezones:
            params['timezone_error'] = "Invalid timezone."
            valid = False

        if not valid:
            self.render( "signup.html", timezones=pytz.common_timezones,
                         **params )
            return

        if not user:
            # Add a new runner to the database
            runner = runners.Runners( username = username, 
                                      password = util.make_pw_hash( 
                    username_code, password ),
                                      twitter = twitter,
                                      youtube = youtube,
                                      twitch = twitch,
                                      timezone = timezone,
                                      num_pbs = 0,
                                      parent = runners.key(),
                                      key_name = username_code )
            if gravatar:
                runner.gravatar = hashlib.md5( gravatar.lower( ) ).hexdigest( )
                
            runner.put( )

            # Update runner in memcache
            self.update_cache_runner( username_code, runner )

            # Update runnerlist in memcache.  Note that this puts the runner
            # at the end of the list, rather than in alphabetical order among
            # those runners with 0 pbs.  The runner will be sorted properly
            # if the memcache gets flushed, which is good enough
            runnerlist = self.get_runnerlist( no_refresh=True )
            if runnerlist is not None:
                runnerlist.append( dict( username = username, 
                                         username_code = username_code,
                                         num_pbs = 0,
                                         gravatar_url = util.get_gravatar_url( 
                                             runner.gravatar ) ) )
                self.update_cache_runnerlist( runnerlist )

            # Update runs for runner in memcache
            self.update_cache_runlist_for_runner( username, [ ] )

            self.login( username_code )
            
        else:
            # Editing the current user
            if len( password ) > 0:
                user.password = util.make_pw_hash( username_code, password )
            user.twitter = twitter
            user.youtube = youtube
            user.twitch = twitch
            user.timezone = timezone
            if gravatar and gravatar != '<private email>':
                user.gravatar = hashlib.md5( gravatar.lower( ) ).hexdigest( )
            elif not gravatar:
                user.gravatar = None
            
            user.put( )

            # Update user in memcache
            self.update_cache_runner( username_code, user )

            # Update runnerlist in memcache if gravatar updated
            if gravatar != '<private email>':
                runnerlist = self.get_runnerlist( no_refresh=True )
                if runnerlist is not None:
                    for runnerdict in runnerlist:
                        if runnerdict['username'] == user.username:
                            runnerdict['gravatar_url'] = util.get_gravatar_url(
                                user.gravatar )
                            break
                    self.update_cache_runnerlist( runnerlist )

        self.redirect( return_url )
