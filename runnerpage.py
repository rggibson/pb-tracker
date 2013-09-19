import handler
import runs
import runners

class RunnerPage(handler.Handler):
    def get(self, username):
        user = self.get_user()

        # Set this page to be the return page after a login/logout/signup
        self.set_return_url('/runner/' + username)

        # Find the runner
        q = runners.Runners.all()
        q.filter('username =', username)
        runner = q.get()
        if not runner:
            self.error(404)
            self.render("404.html", user=user)
            return

        pblist = self.get_pblist(username)
        
        self.render("runnerpage.html", user=user, username=username, 
                    pblist=pblist)
