#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from utfurl import fixurl

mimetypes.init()

TOP = u"/home/media/audio/ReTagged/"

Base = declarative_base()

class scannerTrack(Base):
    __tablename__ = 'tracks'
    filepath = Column(String(512), primary_key=True)
    aid = Column(String(48))
    tid = Column(String(48))

    def __init__(self, filepath):
        self.filepath = filepath
        self.aid = ""
        self.tid = ""
  
    def __repr__(self):
        return "<Track (%s - %s plays, %s skips, last played %s)>" % (self.filepath, self.playcount, self.skipcount, self.lastplayed)


def connect():
    engine = create_engine('sqlite:///scanner.db', echo=False)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return(Session())


class Scanner:

    def __init__(self, filelist):
        self.track = None

        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)
        self.player.set_property("audio-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        
        self.filelist = filelist

        self.session = connect()
    

    def scan(self):
        if os.path.isfile(self.filepath):
            self.player.set_property("uri", "file://" + fixurl(self.filepath.replace("#","%23")))
            self.player.set_state(gst.STATE_PLAYING)
            print("Scanning %s" % self.filepath)


    def stop(self):
        if self.player.get_state() != gst.STATE_NULL:
            self.player.set_state(gst.STATE_NULL)
            if self.track:
                self.session.add(self.track)
            self.session.commit()


    def next(self):
        self.stop()
        if len(self.filelist) > 0:
            self.filepath = self.filelist.pop()
            self.track = scannerTrack(self.filepath)
            self.scan()
        else:
            gtk.main_quit()


    def on_message(self, bus, message):
        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
            self.stop()
            print("Hit end of %s" % self.filepath)
            self.next()

        elif t == gst.MESSAGE_ERROR: # Eeek!
            self.stop()
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)

        elif t == gst.MESSAGE_TAG:
                taglist = message.parse_tag()
                keys = taglist.keys()
                if "musicbrainz-trackid" in keys and "musicbrainz-albumid" in keys:
                    self.track.tid = taglist["musicbrainz-trackid"]
                    self.track.aid = taglist["musicbrainz-albumid"]
                    self.next()



if __name__ == "__main__":
    filelist = []
    for root, dirs, files in os.walk(TOP):
        for f in files:
            filepath = "%s/%s" % (root, f)
            mimetype = mimetypes.guess_type(filepath)
            if type(mimetype) is tuple:
                mimetype = mimetype[0]
            if mimetype and "audio" in mimetype:
                filelist.append(filepath)

    p = Scanner(filelist)
    p.next()

    gtk.main()

