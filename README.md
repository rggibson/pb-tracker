PB Tracker
==========

PB Tracker is a web app for tracking [speedrunning](http://en.wikipedia.org/wiki/Speedrun) times and personal bests.  Users can browse individual runners and games, and view runs submitted for each runner and game respectively.  In addition, users may signup for their own account, submit their own runs and view / maintain their own individual runner page.

Technical Overview
------------------

PB Tracker is written mainly in Python and is deployed on [Google App Engine (GAE)](https://developers.google.com/appengine/).  HTML templating is done with [Jinja2](http://jinja.pocoo.org/), while style and layout is achieved through [Twitter Bootstrap](http://getbootstrap.com/), [Font Awesome](http://fortawesome.github.io/Font-Awesome/whats-new/) and [Bootswatch](http://bootswatch.com/).  To run your own development copy of PB Tracker, first download and install the [GAE SDK for Python](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).  Next, clone the repository and run `dev_appserver.py /path/to/pb-tracker-directory/` or on Mac and Windows, load the project in GAE's development GUI and run.  Finally, open up a browser to `http://localhost:8080` (or replace `8080` with a different port if you specified one).

Database Entities
-----------------

At the time of writing this document, PB Tracker stores three types of entities.  These types are configured in three corresponding python classes:

  * `runners.py` - Stores runner (user) info.  Passwords are stored encrypted with sha256 and salt (see `util.make_pw_hash`), while Gravatar emails are also stored encrypted with md5 as needed for [Gravatar usage](http://en.gravatar.com/site/implement/images/).
  * `runs.py` - Stores submitted runs.  Run times are stored in seconds and converted to hh:mm:ss with `util.seconds_to_timestr` when required.
  * `games.py` - Stores game, category and best known time information.  Categories and best known times are stored as JSON text with the following keys: `category`, `bk_runner`, `bk_seconds`, `bk_datestr`, `bk_video` and `bk_updater` (hidden field).  The date of the best known run, `bk_datestr`, is stored as a 'mm/dd/yyyy' string and is converted to a Python `Date` object with `util.datestr_to_date` when required.  Finally, `games.py` also stores the number of pbs tracked for each game.  This is an optimization measure as the query required to calculate this number is expensive.
  

