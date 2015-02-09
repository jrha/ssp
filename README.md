SSP
===

A wear levelling player for your music collection.
Like a radio station that plays all of your music with a no repeat guarantee!

Features
--------
* Only five controls.
* Tracks are shuffled to equalise play count.
* Skipped tracks are demoted in play order.

Controls
--------
* __ESC__ - Exit
* __Space__ - Skip current track
* __a__ - Toggle album mode
* __e__ - Toggle exit after current track completes
* __p__ - Flag problem with current track and skip it

Requirements
------------
* python-sqlalchemy
* pygtk
* A collection of music with musicbrainz tags (use Picard)

Getting Started
---------------
* Run `./update_library.py` which may take a while.
* Run `./player.py`.
* Enjoy.

Album Mode
------------
Play randomly selected albums from start to finish, ignoring tracks that have been played or skipped this round.
Toggle with the `a` key at runtime and/or start the player in album mode with `--albums`.

Passive Mode
------------
If for some reason you don't want the player to update statistics in the library,
run with `--passive`, this is probably only useful if you are testing something.
Album Mode will play one track forever in passive mode as it relies on track statistics.

Flagging Problem Tracks
-----------------------
If you come across a track which has problems (skipping audio, distortion, doesn't finish playing...)
press `p` to skip it and write a message to the player log flagging the track as problematic.
Find these messages later by searching for __PROBLEM__ in the log file, e.g. `grep PROBLEM ssp.log`.
