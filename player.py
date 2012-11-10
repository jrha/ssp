#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst
import pango
from datetime import datetime

from library import *

class Player:


    def __init__(self):
        self.trackinfo = ""
        self.library = connect()

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

        self.window.add(self.label)

        self.window.show_all()

        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
    

    def key_press(self, widget, event, data=None):
        #Only exit if window is closed or Escape key is pressed
        if event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) == "space":
            self.skip()
            return True
        elif event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) != "Escape":
            return True
        else:
            gtk.main_quit()
            return False


    def play(self):
        self.track = self.library.query(sspTrack).order_by(sspTrack.playcount + sspTrack.skipcount, "random()").first()
        self.filepath = self.track.filepath # shortcut

        if os.path.isfile(self.filepath):
            self.player.set_property("uri", "file://" + self.filepath)
            self.player.set_state(gst.STATE_PLAYING)


    def skip(self):
        self.stop()
        # Increment skip count
        self.track.skipcount += 1
        self.library.commit()
        self.play()


    def stop(self):
        self.player.set_state(gst.STATE_NULL)


    def on_message(self, bus, message):
        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
            # Increment play count, set last played
            self.track.playcount += 1
            self.track.lastplayed = datetime.now()
            self.library.commit()
            self.stop()
            self.play()

        elif t == gst.MESSAGE_ERROR: # Eeek!
            self.stop()
            err, debug = message.parse_error()
            print "Error: %s" % err, debug

        elif t == gst.MESSAGE_TAG:
                taglist = message.parse_tag()
                keys = taglist.keys()
                if "title" in taglist:
                    self.trackinfo = '%s' % taglist["title"]
                    if "artist" in taglist:
                        self.trackinfo += '\n%s' % taglist["artist"]
                    if "album" in taglist:
                        self.trackinfo += '\n%s' % taglist["album"]
                        if "date" in taglist:
                            self.trackinfo += ' (%s)' %  taglist["date"].year

                    self.label.set_label(self.trackinfo)
                    self.window.set_title("SSP : %s" % (self.trackinfo.replace("\n", " - ")))




if __name__ == "__main__":
    p = Player()
    p.play()
    gtk.main()
