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
parser = argparse.ArgumentParser(description='Super Simple Player - Deduplicator')
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
from sqlalchemy import func, alias
from datetime import datetime

from utfurl import fixurl

from library import *
from sqlalchemy.exc import IntegrityError

mimetypes.init()

class Deduper:

    def __init__(self, session, tracklist):
        self.logger = logging.getLogger("ssp-deduper")

        self.track = None

        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)
        self.player.set_property("audio-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.tracklist = tracklist
        self.files = []
        self.votes = []
        self.tags = {}

        self.logger.debug("Connecting to database")
        self.session = session


    def scan(self):
        if os.path.isfile(self.track.filepath):
            self.player.set_property("uri", u"file://" + fixurl(self.track.filepath.replace("#","%23")))
            self.player.set_state(gst.STATE_PLAYING)
            self.logger.debug(u"Scanning %s" % self.track.filepath)
        else:
            self.stop()
            self.logger.error(u"Unable to find %s on disk" % (self.track.filepath))
            self.next()


    def stop(self):
        if self.player.get_state() != gst.STATE_NULL:
            self.player.set_state(gst.STATE_NULL)


    def next(self):
        self.stop()
        if len(self.tracklist) > 0:
            if len(self.files) == 0:
                if self.votes:
                    self.logger.debug(u"Votes are in!")
                    self.votes.sort(reverse=True)
                    self.logger.debug("Keep File with vote %d: %s" % self.votes[0])
                    keeptrack = session.query(sspTrack).filter(sspTrack.filepath == self.votes[0][1]).first()
                    self.logger.debug("Keep Object: %s" % keeptrack)
                    for v in self.votes[1:]:
                        self.logger.info("Delete File with vote %d: %s" % v)
                        os.remove(v[1])
                        deltrack = session.query(sspTrack).filter(sspTrack.filepath == v[1]).first()
                        self.logger.info("Delete Object: %s" % deltrack)
                        session.delete(deltrack)
                        keeptrack.playcount += deltrack.playcount
                        keeptrack.skipcount += deltrack.skipcount
                        if keeptrack.lastplayed and deltrack.lastplayed:
                            if keeptrack.lastplayed < deltrack.lastplayed:
                                keeptrack.lastplayed = deltrack.lastplayed
                        elif not keeptrack.lastplayed and deltrack.lastplayed:
                            keeptrack.lastplayed = deltrack.lastplayed
                    session.commit()
                    self.logger.debug("Merged Object: %s" % keeptrack)
                    self.votes = []
                self.logger.debug(u"Popping TrackID")
                self.albumid, self.trackid = self.tracklist.pop()
                self.files = self.session.query(sspTrack.filepath).filter(sspTrack.albumid == self.albumid, sspTrack.trackid == self.trackid).all()
            self.logger.debug(u"Popping File")
            self.track = self.files.pop()
            self.vote = 0
            self.scan()
            remaining = len(tracklist)
            if remaining % 100 == 0:
                self.logger.info("%d tracks remaining" % (remaining))
        else:
            gtk.main_quit()


    def on_message(self, bus, message):
        # We don't know what order these come in,
        # so we need to deal with them as they come
        # and skip when we've got everything we need

        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
            self.stop()
            self.logger.debug(u"Hit end of %s" % self.track.filepath)
            self.logger.debug(self.track)

            tags = self.tags
            keys = tags.keys()
            self.tags = {}

            vote = 0

            for k in "bitrate", "nominal-bitrate":
                if k in keys:
                    if   tags[k] >= 256000: vote += 3
                    elif tags[k] >= 192000: vote += 2
                    elif tags[k] >= 160000: vote += 1
                    # 128kbps is baseline
                    elif tags[k] <=  96000: vote -= 1
                    elif tags[k] <=  64000: vote -= 2

            if "channel-mode" in keys:
                if tags["channel-mode"] == "stereo": vote += 3
                elif tags["channel-mode"] == "joint-stereo": vote += 2

            if "audio-codec" in keys:
                if   "FLAC" in tags["audio-codec"]: vote += 8
                elif "OGG"  in tags["audio-codec"]: vote += 4
                elif "MP3"  in tags["audio-codec"]: vote += 1

            self.logger.debug("Vote = %s" % vote)
            self.votes.append((vote, self.track.filepath))
            self.next()

        elif t == gst.MESSAGE_ERROR: # Eeek!
            self.stop()
            err, debug = message.parse_error()
            self.logger.error("Hit an error scanning %s" % self.track.filepath)
            self.logger.error("%s\t%s" % (err, debug))

        elif t == gst.MESSAGE_TAG:
                taglist = message.parse_tag()
                keys = taglist.keys()

                for k in keys:
                    if "private" not in k and "extended" not in k:
                        self.logger.debug("Found tag: %32s : %s" % (k, taglist[k]))
                        self.tags[k] = taglist[k]



if __name__ == "__main__":
    logger = logging.basicConfig(level=logging.INFO, format='%(asctime)s L%(lineno)03d %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', name="ssp-deduper")
    logger = logging.getLogger("ssp-deduper")
    session = connect()

    if args.debug:
        logger.level = logging.DEBUG
    tracklist = []

    tracklist = session.query(sspTrack.albumid, sspTrack.trackid, func.count(sspTrack.trackid)).group_by(sspTrack.albumid, sspTrack.trackid).all()
    tracklist = [ (albumid, trackid) for albumid, trackid, count in tracklist if count > 1 ]

    logger.info("%d tracks need deduping" % (len(tracklist)))
    if len(tracklist) > 0:
        logger.info("Starting dedupe")
        d = Deduper(session, tracklist)
        d.next()
        gtk.main()
        logger.info("Deduper finished, exiting")
    else:
        logger.info("No deupe necessary, exiting")

