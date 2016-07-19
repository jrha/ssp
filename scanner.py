#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2012  James Adams
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
parser = argparse.ArgumentParser(description='Super Simple Player - Library Updater')
parser.add_argument('--debug', action="store_true", help="Print lots of debugging information while running")
group_top = parser.add_mutually_exclusive_group()
group_top.add_argument('--all', action="store_true", help="Rescan all tracks, even if they have already been scanned")
group_top.add_argument('--hours', action="store", type=int, default=0, help="Scan tracks that have not been scanned in the last X hours")
group_top.add_argument('--days', action="store", type=int, default=0, help="Scan tracks that have not been scanned in the last Y days")
group_top.add_argument('--keyword', action="store", type=str, default=0, help="Scan tracks with the keyword Z in their file path")
args = parser.parse_args()
del parser

import os
import gtk
import pygst
pygst.require("0.10")
import gst
from datetime import datetime, timedelta
import mimetypes
import logging

from utfurl import fixurl

from library import *

mimetypes.init()

class Scanner:

    def __init__(self, session, tracklist):
        self.logger = logging.getLogger("ssp-scanner")

        self.track = None

        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)
        self.player.set_property("audio-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.tracklist = tracklist

        self.logger.debug("Connecting to database")
        self.session = session


    def scan(self):
        if os.path.isfile(self.track.filepath):
            self.player.set_property("uri", u"file://" + fixurl(self.track.filepath.replace("#","%23")))
            self.player.set_state(gst.STATE_PLAYING)
            self.logger.debug(u"Scanning %s", self.track.filepath)
        else:
            self.stop()
            self.logger.error(u"Unable to find %s on disk", self.track.filepath)
            self.next()


    def stop(self):
        if self.player.get_state() != gst.STATE_NULL:
            self.player.set_state(gst.STATE_NULL)


    def next(self):
        self.stop()
        if len(self.tracklist) > 0:
            self.track = self.tracklist.pop()
            self.scan()
            remaining = len(tracklist)
            if remaining % 100 == 0:
                self.logger.info("%d tracks remaining, session committed up to this point", remaining)
                session.commit()
        else:
            self.session.commit()
            gtk.main_quit()


    def on_message(self, bus, message):
        # We don't know what order these come in,
        # so we need to deal with them as they come
        # and skip when we've got everything we need

        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
            self.stop()
            self.logger.debug(u"Hit end of %s", self.track.filepath)
            self.logger.debug(self.track)
            self.next()

        elif t == gst.MESSAGE_ERROR: # Eeek!
            self.stop()
            self.session.commit()
            err, debug = message.parse_error()
            self.logger.error("Hit an error scanning %s, session committed up to this point", self.track.filepath)
            self.logger.error("%s\t%s", err, debug)
            self.next()

        elif t == gst.MESSAGE_TAG:
            taglist = message.parse_tag()
            keys = taglist.keys()
            if "musicbrainz-trackid" in keys:
                self.track.trackid = taglist["musicbrainz-trackid"]
                self.track.lastscanned = datetime.now()
                self.logger.debug("Got track ID = %s", self.track.trackid)
            if "musicbrainz-albumid" in keys:
                self.track.albumid = taglist["musicbrainz-albumid"]
                self.track.lastscanned = datetime.now()
                self.logger.debug("Got album ID = %s", self.track.albumid)

        recently_scanned = self.track.lastscanned > (datetime.now() - timedelta(minutes=1))
        if self.track.trackid and self.track.albumid and self.track.lastscanned and recently_scanned:
            self.next()



if __name__ == "__main__":
    logger = logging.basicConfig(level=logging.INFO, format='%(asctime)s L%(lineno)03d %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', name="ssp-scanner")
    logger = logging.getLogger("ssp-scanner")
    session = connect()

    if args.debug:
        logger.level = logging.DEBUG
    tracklist = []

    if args.all:
        tracklist = session.query(sspTrack).all()
    elif args.hours or args.days:
        tracklist = session.query(sspTrack).filter(
            (sspTrack.lastscanned == None) | (sspTrack.trackid == '') |
            (sspTrack.lastscanned < datetime.now() - timedelta(hours=args.hours, days=args.days))
        ).all()
    elif args.keyword:
        tracklist = session.query(sspTrack).filter(sspTrack.filepath.like('%%%s%%' % args.keyword)).all()
    else:
        tracklist = session.query(sspTrack).filter((sspTrack.trackid == None) | (sspTrack.trackid == '')).all()

    logger.info("%d tracks need tags scanning", len(tracklist))
    if len(tracklist) > 0:
        logger.info("Starting tag scan")
        p = Scanner(session, tracklist)
        p.next()
        gtk.main()
        session.commit()
        logger.info("Scanner finished, committing changes and exiting")
    else:
        logger.info("No tracks to scan, exiting")
