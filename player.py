#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2012, 2013  James Adams
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#


# Icky work-around for the gst module setting up it's own parser... the bastard...
import argparse
parser = argparse.ArgumentParser(description='Super Simple Player')
parser.add_argument('--passive', action='store_true', help="Don't update track statistics.")
parser.add_argument('--albums', action='store_true', help="Album mode, randomly select an album to play rather than a track.")
parser.add_argument('--debug', action='store_true', help="Enable debug logging.")
args = parser.parse_args()
del parser

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import pango
from gst import element_factory_make, STATE_PLAYING, STATE_NULL, MESSAGE_EOS, MESSAGE_ERROR, MESSAGE_TAG
from datetime import datetime
import logging
import pynotify
import random
import json

from utfurl import fixurl

from library import *

class TrackInfo(object):
    def __init__(self):
        self.title = ""
        self.artist = ""
        self.album = ""
        self.year = ""

    def tolabel(self):
        s = "%s\n%s\n%s" % (self.title, self.artist, self.album)
        if self.year:
            s += " (%s)" % (self.year)
        return s

    def totitle(self, extras = ""):
        s = "SSP : %s - %s - %s" % (self.title, self.artist, self.album)
        if self.year:
            s += " (%s)" % (self.year)
        return s + extras

    def tonotification(self):
        s = "%s\n%s" % (self.artist, self.album)
        if self.year:
            s += " (%s)" % (self.year)
        return (self.title, s)


class Player(object):

    def __init__(self, passive=False, album_mode=False):
        self.logger = logging.getLogger("ssp")
        self.logger.info("Startup, passive mode %s, album mode %s, library schema v%s", passive, album_mode, SCHEMA_VERSION)

        self.passive = passive
        self.album_mode = album_mode
        self.exit_after_current = False
        self.album = "ssp-rocks-your-socks-off"
        self.trackinfo = TrackInfo()
        self.library = connect()
        self.logger.debug("Connected to library")

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("SSP")

        self.window.connect("destroy", gtk.main_quit, "WM destroy")
        self.window.connect("delete_event", self.key_press)
        self.window.connect("key_press_event", self.key_press)

        self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000"))

        self.label = gtk.Label()

        self.label.modify_font(pango.FontDescription("Sans 32"))
        self.label.set_alignment(0.5, 0.5)
        self.label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#eeeeec"))
        self.label.set_line_wrap(True)

        self.window.add(self.label)

        self.window.show_all()

        self.player = element_factory_make("playbin2", "player")
        fakesink = element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        pynotify.init("SSP")
        self.notification = pynotify.Notification("SSP")


    def updateTitle(self):
        s = ""
        if self.album_mode:
            s = " [Album Mode]"
        if self.exit_after_current:
            s += " [Exit After Current]"
        self.window.set_title(self.trackinfo.totitle(s))


    def key_press(self, _, event, _):
        #Only exit if window is closed or Escape key is pressed
        if event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) == "space":
            self.skip()
            return True
        elif event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) == "a":
            self.album_mode = not self.album_mode
            self.logger.debug("Changed album mode to %s", self.album_mode)
            self.updateTitle()
            return True
        elif event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) == "p":
            self.flag_problem()
            return True
        elif event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) == "e":
            self.exit_after_current = not self.exit_after_current
            self.logger.debug("Changed exit after current to %s", self.exit_after_current)
            self.updateTitle()
            return True
        elif event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) != "Escape":
            return True
        else:
            self.state_save()
            gtk.main_quit()
            return False

    def state_save(self, blank=False):
        f = open(os.path.join(os.path.dirname(sys.argv[0]), 'state.json'), 'w')
        if not blank:
            try:
                d = {
                    'trackid' : self.track.trackid,
                    'album_mode' : self.album_mode,
                }
            except AttributeError:
                d = {}
        else:
            d = {}
        self.logger.info("Saved State: %s", d)
        json.dump(d, f)

    def state_restore(self):
        f = open(os.path.join(os.path.dirname(sys.argv[0]), 'state.json'), 'r')
        try:
            d = json.load(f)
        except ValueError:
            d = {}
        self.logger.info("Restored State: %s", d)
        return(d)

    def select_random(self, min_play_count, min_skip_count):
        self.logger.debug("Selecting track based on standard algorithm")
        track = random.choice(self.library.query(sspTrack).filter(sspTrack.playcount == min_play_count).filter(sspTrack.skipcount == min_skip_count).all())
        return track

    def select_track(self, trackid):
        self.logger.debug("Specified trackid, locating track")
        track = self.library.query(sspTrack).filter(sspTrack.trackid == trackid).first()
        return track

    def select_album(self, min_play_count, min_skip_count, album):
        self.logger.debug("Selecting track based on album mode algorithm")
        self.logger.debug("min_play_count: %s", min_play_count)
        self.logger.debug("min_skip_count: %s", min_skip_count)
        remaining_album_tracks = self.library.query(sspTrack).filter(sspTrack.playcount == min_play_count).filter(sspTrack.skipcount == min_skip_count).filter(sspTrack.albumid == album).count()
        self.logger.debug("remaining_album_tracks: %s", remaining_album_tracks)
        if remaining_album_tracks == 0:
            self.logger.debug("No tracks left to play, selecting new album")
            album = self.library.query(sspTrack.albumid).filter(sspTrack.playcount == min_play_count).filter(sspTrack.skipcount == min_skip_count).order_by(sspTrack.playcount + sspTrack.skipcount, "random()").first()[0]
        self.logger.debug("Album ID: %s", album)
        track = self.library.query(sspTrack).filter(sspTrack.albumid == album).filter(sspTrack.playcount == min_play_count).filter(sspTrack.skipcount == min_skip_count).filter(sspTrack.albumid == album).order_by(sspTrack.filepath).first()
        if track.skipcount > min_skip_count or track.playcount > min_play_count or track.albumid != album:
            self.logger.error("Algorithm failure, selected track doesn't meet selection conditions. This is a bug, report this!")

        return track

    def play(self, trackid=None):
        min_play_count = self.library.query(func.min(sspTrack.playcount)).first()[0]
        min_skip_count = self.library.query(func.min(sspTrack.skipcount)).first()[0]

        # Are we restoring a previous state?
        if not trackid:
            self.logger.debug("Did not specify trackid")
            if self.album_mode:
                # Super happy album mode
                self.track = self.select_album(min_play_count, min_skip_count, self.album)
            else:
                # Regular ordinary ssp time
                self.track = self.select_random(min_play_count, min_skip_count)
        else:
            # Try to find track based on trackid
            self.track = self.select_track(trackid)

        self.album = self.track.albumid # Set this so we can continue with an album


        self.logger.debug("Selected track %s", self.track)

        self.stat = self.library.query(sspStat).filter("hour = %s" % datetime.now().hour).first()
        if not self.stat:
            self.stat = sspStat(datetime.now().hour)
            self.library.add(self.stat)

        self.weekstat = self.library.query(sspWeekStat).filter("hour = %s" % datetime.now().hour).filter("day = %s" % datetime.now().weekday()).first()
        if not self.weekstat:
            self.weekstat = sspWeekStat(datetime.now().hour, datetime.now().weekday())
            self.library.add(self.weekstat)

        self.trackinfo = TrackInfo()

        if os.path.isfile(self.track.filepath):
            self.player.set_property("uri", u"file://" + fixurl(self.track.filepath.replace("#","%23")))
            self.state_save()
            self.player.set_state(STATE_PLAYING)
        else:
            self.logger.info("Oops, \"%s\" doesn't seem to exist anymore", self.track.filepath)
            self.stop()
            self.play()


    def skip(self):
        self.stop()
        if not self.passive:
            # Increment skip count
            self.track.skipcount += 1
            self.stat.skipcount += 1
            self.weekstat.skipcount += 1
            self.library.commit()
            self.logger.debug("Updated stats on skip %s", self.track)
        self.play()


    def flag_problem(self):
        self.logger.info("PROBLEM flagged with %s", self.track)
        self.skip()


    def stop(self):
        self.state_save(True)
        self.player.set_state(STATE_NULL)


    def on_message(self, _, message):
        t = message.type

        if t == MESSAGE_EOS: # End Of Stream
            self.stop()
            if self.exit_after_current:
                gtk.main_quit()
                return False
            if not self.passive:
                # Increment play count, set last played
                self.track.playcount += 1
                self.stat.playcount += 1
                self.weekstat.playcount += 1
                self.track.lastplayed = datetime.now()
                self.library.commit()
                self.logger.debug("Updated stats on play completion %s", self.track)
            self.play()

        elif t == MESSAGE_ERROR: # Eeek!
            self.stop()
            err, debug = message.parse_error()
            self.logger.error("MESSAGE_ERROR: %s", err, debug)

        elif t == MESSAGE_TAG:
            taglist = message.parse_tag()
            if "title" in taglist:
                self.trackinfo.title = taglist["title"]
                if "artist" in taglist:
                    self.trackinfo.artist = taglist["artist"]
                if "album" in taglist:
                    self.trackinfo.album = taglist["album"]
                    if "date" in taglist:
                        self.trackinfo.year = str(taglist["date"].year)

                self.label.set_label(self.trackinfo.tolabel())
                self.updateTitle()
                self.notify(self.trackinfo.tonotification())


    def notify(self, message):
        self.notification.update(message[0], message[1], "media-skip-forward")
        self.notification.show()


if __name__ == "__main__":
    logger = logging.basicConfig(filename='%s/ssp.log' % os.path.dirname(sys.argv[0]), level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', name="ssp")
    logger = logging.getLogger("ssp")
    if args.debug:
        logger.setLevel(logging.DEBUG)

    p = Player(args.passive, args.albums)

    restore = p.state_restore()
    if restore:
        p.album_mode = restore['album_mode']
        p.play(restore['trackid'])
    else:
        p.play()

    gtk.main()

    logger.info("Shutdown")
