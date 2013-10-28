PB Tracker
==========

PB Tracker is a web app for tracking [speedrunning](http://en.wikipedia.org/wiki/Speedrun) times and personal bests.  Users can browse individual runners and games, and view runs submitted for each runner and game respectively.  In addition, users may signup for their own account, submit their own runs and view / maintain their own individual runner page.

Technical Overview
------------------

PB Tracker is written mainly in Python and is deployed on [Google App Engine (GAE)](https://developers.google.com/appengine/).  To run your own development copy of PB Tracker, first download and install the [GAE SDK for Python](https://developers.google.com/appengine/downloads#Google_App_Engine_SDK_for_Python).  Next, clone the repository and run `dev_appserver.py /path/to/pb-tracker-directory/` or on Mac and Windows, load the project in GAE's development GUI and run.  Finally, open up a browser to `http://localhost:8080` (or replace `8080` with a different port if you specified one).

