#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gst
import pango
from random import randint

from library import *

SELECT_LIMIT = 128

class Player:


    def __init__(self):
        self.trackinfo = ""
        self.library = connect()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Audio-Player")

        self.window.connect("destroy", gtk.main_quit, "WM destroy")
        self.window.connect("delete_event", self.key_press)
        self.window.connect("key_press_event", self.key_press)

        self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000"))

        self.label = gtk.Label()
        self.label.modify_font(pango.FontDescription("Sans 48"))
        self.label.set_alignment(0.5, 0.5)
        self.label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#eeeeec"))

        self.window.add(self.label)

        self.window.fullscreen()
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
        tracks = self.library.query(sspTrack).order_by(sspTrack.playcount).limit(SELECT_LIMIT).all()
        self.track = tracks[randint(0, SELECT_LIMIT)]
        self.filepath = track.filepath # shortcut
        print("Playing %s" % self.filepath)

        if os.path.isfile(self.filepath):
            self.player.set_property("uri", "file://" + self.filepath)
            self.player.set_state(gst.STATE_PLAYING)
            #print("PLAYING: %s" % filepath)


    def skip(self):
        self.stop()
        print("Skipped %s" % self.filepath)
        # Increment skip count
        self.track.skip
        self.play()


    def stop(self):
            self.player.set_state(gst.STATE_NULL)


    def on_message(self, bus, message):
        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
            # Increment play count, set last played
            self.stop()
            print("Completed %s" % self.filepath)
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




if __name__ == "__main__":
    p = Player()
    p.play()
    gtk.main()
