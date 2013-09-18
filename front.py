import handler

class Front(handler.Handler):
    def get(self):
        user = self.get_user()

        # Set this page to be the return page after a login/logout/signup
        self.set_return_url('/')
                
        self.render( "front.html", user=user )
