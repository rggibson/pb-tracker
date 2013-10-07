import handler
import runners
import util

class Login(handler.Handler):
    def get(self):
        self.render("login.html")

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')
        username_code = util.get_code( username )

        # Find the user in the database
        user = runners.Runners.get_by_key_name( username_code,
                                                parent=runners.key() )
        if not user:
            self.render( "login.html", username=username, 
                         error="Invalid login" )
            return

        # Check for valid password
        if util.valid_pw( username_code, password, user.password ):
            self.login( username_code )
            self.goto_return_url( )
        else:
            self.render( "login.html", username=username, 
                         error="Invalid login" )
