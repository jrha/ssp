SSP
===

A wear levelling player for your music collection.
Like a radio station that plays all of your music with a no repeat guarantee!

Features
--------
* Only two controls.
* Tracks are shuffled to equalise play count.
* Skipped tracks are demoted in play order.
* Missing tracks are automatically removed from the library.

Controls
--------
* __ESC__ - Exit
* __Space__ - Skip current track
* __a__ - Toggle album mode


Requirements
------------
* python-sqlalchemy
* pygtk
* A collection of music


Getting Started
---------------
* Run `./update_library.py` which may take a while.
* Run `./player.py`.
* Enjoy.

Album Mode
------------
Play randomly selected albums from start to finish, skipping tracks if they have been played or skipped previously.
Toggle with the `a` key at runtime and/or start the player in album mode with `--album`.

Passive Mode
------------
If for some reason you don't want the player to update statistics in the library,
run with `--passive`, this is probably only useful if you are testing something.
