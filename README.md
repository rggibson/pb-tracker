PB Tracker
==========

PB Tracker is a web app for tracking [speedrunning](http://en.wikipedia.org/wiki/Speedrun) times and personal bests (PBs).  Users can browse individual runners and games, and view runs submitted for each runner and game respectively.  In addition, users may signup for their own account, submit their own runs and view / maintain their own individual runner page.

Technical Overview
------------------

PB Tracker is written mainly in Python under the [webapp2 framework](http://webapp-improved.appspot.com/) and is deployed on [Google App Engine (GAE)](https://developers.google.com/appengine/).  HTML templating is done with [Jinja2](http://jinja.pocoo.org/), while style and layout is achieved through [Twitter Bootstrap](http://getbootstrap.com/), [Font Awesome](http://fortawesome.github.io/Font-Awesome/whats-new/) and [Bootswatch](http://bootswatch.com/).  To run your own development copy of PB Tracker, first download and install the [GAE SDK for Python](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).  Next, clone the repository and run `dev_appserver.py /path/to/pb-tracker-directory/` or on Mac and Windows, load the project in GAE's development GUI and run.  Finally, open up a browser to `http://localhost:8080` (or replace `8080` with a different port if you specified one).

Database Entities
-----------------

At the time of writing this document, PB Tracker stores three types of entities.  These types are configured in three corresponding python classes:

  * `runners.py` - Stores runner (user) info.  Passwords are stored encrypted with sha256 and salt (see `util.make_pw_hash`), while Gravatar emails are also stored encrypted with md5 as needed for [Gravatar usage](http://en.gravatar.com/site/implement/images/).
  * `runs.py` - Stores submitted runs.  Run times are stored in seconds and converted to hh:mm:ss with `util.seconds_to_timestr` when required.
  * `games.py` - Stores game, category and best known time information.  Categories and best known times are stored as JSON text with the following keys: `category`, `bk_runner`, `bk_seconds`, `bk_datestr`, `bk_video` and `bk_updater` (hidden field).  The date of the best known run, `bk_datestr`, is stored as a 'mm/dd/yyyy' string and is converted to a Python `Date` object with `util.datestr_to_date` when required.  Finally, `games.py` also stores the number of pbs tracked for each game.  This is an optimization measure as the query required to calculate this number is expensive.
  
Python Classes
--------------

 * `main.py` - Launch point for the app.  Defines all of the URL handles, including an error handler for all non-matching URLs.
 * `front.py` - The homepage for the app.  Nothing special here.
 * `runnerlist.py` - Lists all runners (users) that have signed up on PB Tracker, sorted by the number of PBs submitted.  This is achieved by calling `handler.get_runnerlist( )` that returns a sorted list of dictionaries containing the relevant information. 
 * `gamelist.py` - Similar to `runnerlist.py`, but lists games instead of runners.
 * `runnerpage.py` - Renders individual runner pages at `/runner/<username_code>`, where `username_code` is the runner's username converted to lower case with most non-alphanumeric characters replaced with dashes (see `util.get_code`).  There are two versions of runner pages.  The default version renders a table of PBs submitted by the runner, ordered by number of runs.  The content of this table is aquired through `handler.get-pblist()` that returns a list of dictionaries, one for each game.  For each dictionary `d`, `d['infolist']` is itself another list of dictionaries, one for each category the runner has run for the given game.  These dictionaries are aquired through `handler.get_runinfo()`. The alternative runner page is rendered given the query string `?q=view-all` and lists all runs, ordered by run date, aquired through `handler.get_runlist_for_runner()`.  This function returns its own list of dictionaries.
