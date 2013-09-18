import handler

class Logout(handler.Handler):
    def get(self):
        # Clear login cookie 
        cookie = 'user_id=;Path=/'
        self.response.headers.add_header('Set-Cookie', cookie)
        self.goto_return_url()
