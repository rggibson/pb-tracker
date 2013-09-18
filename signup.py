import handler
import runners
import re
import util

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{1,20}$")
def valid_username(username):
    return USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return PASS_RE.match(password)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return EMAIL_RE.match(email)


class Signup(handler.Handler):
    def get(self):
        self.render("signup.html")

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        params = dict( username = username,
                       password = password,
                       verify = verify,
                       email = email )

        valid = True

        if not valid_username(username):
            params['user_error'] = "Username must be between 1 and 20 characters."
            valid = False
        else:
            # Check if username already exists
            q = runners.Runners.all()
            q.filter('username =', username)
            if q.get():
                params['user_error'] = "That user already exists."
                valid = False
        
        if not valid_password(password):
            params['pass_error'] = "Password must be between 3 and 20 characters."
            valid = False

        if password != verify:
            params['ver_error'] = "Passwords do not match."
            valid = False

        if email != "" and not valid_email(email):
            params['email_error'] = "That's not a valid email."
            valid = False

        if not valid:
            self.render("signup.html", **params)

        else:
            # Add a runner to the database
            runner = runners.Runners(username = username, 
                                     password = util.make_pw_hash(username, 
                                                                  password), 
                                     email = email,
                                     parent = runners.key())
            runner.put()
            runner_id = runner.key().id()
            self.login(runner_id)
            self.goto_return_url()
