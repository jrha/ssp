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
args = parser.parse_args()
del parser

import sys, os
import gtk
import pygst
pygst.require("0.10")
import gst
import pango
from datetime import datetime
import mimetypes
import json
import urllib
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from utfurl import fixurl

from library import *
from sqlalchemy.exc import IntegrityError

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
            self.logger.debug(u"Scanning %s" % self.track.filepath)


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
                self.logger.info("%d tracks remaining, session committed up to this point" % (remaining))
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
            self.logger.debug(u"Hit end of %s" % self.filepath)
            self.logger.debug(self.track)
            self.next()

        elif t == gst.MESSAGE_ERROR: # Eeek!
            self.stop()
            self.session.commit()
            err, debug = message.parse_error()
            self.logger.error("Hit an error scanning %s, session committed up to this point" % self.track.filepath)
            self.logger.error("%s\t%s" % (err, debug))

        elif t == gst.MESSAGE_TAG:
                taglist = message.parse_tag()
                keys = taglist.keys()
                if "musicbrainz-trackid" in keys and "musicbrainz-albumid" in keys:
                    self.track.trackid = taglist["musicbrainz-trackid"]
                    self.track.albumid = taglist["musicbrainz-albumid"]
                    self.logger.debug("Got IDs\ttrack = %s\talbum = %s" % (self.track.trackid, self.track.albumid) )
                #elif "nominal-bitrate" in keys:
                #    self.track.bitrate = taglist["nominal-bitrate"]
                #elif "bitrate" in keys:
                #    self.track.bitrate = taglist["bitrate"]
                #elif "channel-mode" in keys:
                #    self.track.channels = taglist["channel-mode"]
                #elif "audio-codec" in keys:
                #    self.track.codec = taglist["audio-codec"]
                else:
                    for k in keys:
                        self.logger.debug("Extra tag: %s\t%s" % (k, taglist[k]))

        if self.track.albumid and self.track.trackid:
            self.next()



if __name__ == "__main__":
    logger = logging.basicConfig(level=logging.INFO, format='%(asctime)s L%(lineno)03d %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', name="ssp-scanner")
    logger = logging.getLogger("ssp-scanner")
    session = connect()

    if args.debug:
        logger.level = logging.DEBUG
    tracklist = []

    tracklist = session.query(sspTrack).filter(sspTrack.trackid == None).all()
    logger.info("%d tracks need tags scanning" % (len(tracklist)))
    if len(tracklist) > 0:
        logger.info("Starting tag scan")
        p = Scanner(session, tracklist)
        p.next()
        gtk.main()
        session.commit()
        logger.info("Scanner finished, committing changes and exiting")
    else:
        logger.info("No tracks to scan, exiting")

