#!/usr/bin/env python
# coding=utf8

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

mimetypes.init()

TOP = u"/home/media/audio/ReTagged/"
OUTFILE = u"scanresults.json"

class Scanner:

    def __init__(self, filelist):
        self.trackinfo = ""

        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)
        self.player.set_property("audio-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        
        self.filelist = filelist
        self.fileinfo = {}
    

    def scan(self):
        if os.path.isfile(self.filepath):
            try:
                self.player.set_property("uri", "file://" + urllib.quote(self.filepath))
                self.player.set_state(gst.STATE_PLAYING)
                print("Scanning %s" % self.filepath)
            except KeyError:
                print("UNICODE FILENAME %s" % self.filepath)
                self.next()
                


    def stop(self):
        self.player.set_state(gst.STATE_NULL)


    def next(self):
        self.stop()
        if len(self.filelist) > 0:
            self.filepath = self.filelist.pop()
            self.scan()
        else:
            f = open(OUTFILE, "w")
            json.dump(self.fileinfo, f, indent=2)
            f.close()
            print("Wrote %s" % OUTFILE)
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
                    self.trackinfo = "%s:%s" % (taglist["musicbrainz-trackid"], taglist["musicbrainz-albumid"])
                    if self.trackinfo not in self.fileinfo:
                        self.fileinfo[self.trackinfo] = []
                    self.fileinfo[self.trackinfo].append(self.filepath)
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

