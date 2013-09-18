import handler
import runners
import util

class Login(handler.Handler):
    def get(self):
        self.render("login.html")

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        # Find the user in the database
        query = runners.Runners.all()
        query.filter("username =", username)
        user = query.get()
        if not user:
            self.render("login.html", username=username, error="Invalid login")
            return

        # Check for valid password
        if util.valid_pw(username, password, user.password):
            user_id = user.key().id()
            self.login(user_id)
            self.goto_return_url()
        else:
            self.render("login.html", username=username, error="Invalid login")
