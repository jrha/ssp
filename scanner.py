#!/usr/bin/env python

import sys, os
import gtk
import pygst
pygst.require("0.10")
import gst
import pango
from datetime import datetime
import mimetypes
import json

mimetypes.init()

TOP = u"/home/media/audio/ReTagged/Eric Clapton/1976 - No Reason to Cry/"

class Scanner:

    def __init__(self, filelist):
        self.trackinfo = ""

        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        
        self.filelist = filelist
        self.fileinfo = {}
    

    def play(self):
        if os.path.isfile(self.filepath):
            self.player.set_property("uri", "file://" + self.filepath)
            self.player.set_state(gst.STATE_PLAYING)
            print("Playing %s" % self.filepath)


    def stop(self):
        self.player.set_state(gst.STATE_NULL)


    def next(self):
        self.stop()
        if len(self.filelist) > 0:
            self.filepath = self.filelist.pop()
            self.play()
        else:
            print(json.dumps(self.fileinfo))
            gtk.main_quit()


    def on_message(self, bus, message):
        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
            self.stop()
            print("Completed %s" % self.filepath)
            self.play()

        elif t == gst.MESSAGE_ERROR: # Eeek!
            self.stop()
            err, debug = message.parse_error()
            print "Error: %s" % err, debug

        elif t == gst.MESSAGE_TAG:
                taglist = message.parse_tag()
                self.trackinfo={}
                for k in taglist.keys():
                    self.trackinfo[k] = taglist[k]

                self.fileinfo[self.filepath] = self.trackinfo
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

