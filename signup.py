import handler
import runners
import re
import util
import hashlib

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
        self.render( "signup.html" )

    def post( self ):
        username = self.request.get( 'username' )
        password = self.request.get( 'password' )
        verify = self.request.get( 'verify' )
        twitter = self.request.get( 'twitter' )
        if twitter[ 0:1 ] == '@':
            twitter = twitter[ 1: ]
        youtube = self.request.get( 'youtube' )
        twitch = self.request.get( 'twitch' )
        gravatar = self.request.get( 'gravatar' )
        username_code = util.get_code( username )

        params = dict( username = username,
                       password = password,
                       verify = verify,
                       twitter = twitter,
                       youtube = youtube,
                       twitch = twitch,
                       gravatar = gravatar )

        valid = True

        if not valid_username( username ):
            params['user_error'] = ( "Username must be between " 
                                     + "1 and 20 characters." )
            valid = False
        else:
            # Check if username already exists
            if self.get_runner( username_code ) is not None:
                params['user_error'] = "That user already exists."
                valid = False
        
        if not valid_password( password ):
            params['pass_error'] = ( "Password must be between "
                                     + "3 and 20 characters." )
            valid = False

        if password != verify:
            params['ver_error'] = "Passwords do not match."
            valid = False

        if gravatar != "" and not valid_email( gravatar ):
            params['gravatar_error'] = "That's not a valid email."
            valid = False

        if not valid:
            self.render( "signup.html", **params )

        else:
            # Add a runner to the database
            runner = runners.Runners( username = username, 
                                      password = util.make_pw_hash( username, 
                                                                    password),
                                      twitter = twitter,
                                      youtube = youtube,
                                      twitch = twitch,
                                      gravatar = hashlib.md5( 
                                          gravatar.lower( ) ).hexdigest( ),
                                      parent = runners.key(),
                                      key_name = username_code )
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
                                         num_pbs = 0 ) )
                self.update_cache_runnerlist( runnerlist )

            # Update runs for runner in memcache
            self.update_cache_runlist_for_runner( username, [ ] )

            # Login and gogo
            self.login( username_code )
            self.goto_return_url( )
