PB Tracker
==========

[PB Tracker](http://www.pbtracker.net) is a web app for tracking [speedrunning](http://en.wikipedia.org/wiki/Speedrun) times and personal bests (PBs).  Users can browse individual runners and games, and view runs submitted for each runner and game respectively.  In addition, users may signup for their own account, submit their own runs and view / maintain their own individual runner page.

Technical Overview
------------------

PB Tracker is written mainly in Python under the [webapp2 framework](http://webapp-improved.appspot.com/) and is deployed on [Google App Engine (GAE)](https://developers.google.com/appengine/).  HTML templating is done with [Jinja2](http://jinja.pocoo.org/), while style and layout is achieved through [Twitter Bootstrap](http://getbootstrap.com/), [Font Awesome](http://fortawesome.github.io/Font-Awesome/whats-new/) and [Bootswatch](http://bootswatch.com/).  To run your own development copy of PB Tracker, first download and install the [GAE SDK for Python](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).  Next, clone the repository and run `dev_appserver.py /path/to/pb-tracker-directory/` or on Mac and Windows, load the project in GAE's development GUI and run.  Finally, open up a browser to `http://localhost:8080` (or replace `8080` with a different port if you specified one).

Code Overview
-------------

The main launching point for the app is `main.py`.  For explanations of each of the Python classes, see the comments at the top of each Python file.

Want to Contribute?
-------------------

Check out the [issues](https://github.com/rggibson/pb-tracker/issues?direction=asc&sort=created&state=open) and let me know if you want to work on any of them.  I'm happy to take pull requests from anyone willing to put in the time to come up with a workable solution.  If you have a feature that you want to work on for PB Tracker and it is not listed on the issues page, drop me a line to make sure that it is a suitable feature for PB Tracker.

Contact
-------

 * Email: [{name-of-site-no-spaces}speedruns{AT}gmail{DOT}com](mailto:<name-of-site-no-spaces>speedruns<AT>gmail<DOT>com)
 * Twitter: [@PBTracking](https://twitter.com/pbtracking)

