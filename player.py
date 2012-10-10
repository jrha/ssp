#!/usr/bin/env python

import sys, os
import pygtk, gtk, gobject
import pygst
import pango
pygst.require("0.10")
import gst

songs = [
    "/home/jrha/Music/ReTagged/The Seatbelts/1998 - Cowboy Bebop: No Disc/04 - Vitamin A.mp3",
    "/home/jrha/Music/ReTagged/The Seatbelts/1998 - Cowboy Bebop: No Disc/10 - Vitamin B.mp3",
    "/home/jrha/Music/ReTagged/The Seatbelts/1998 - Cowboy Bebop: No Disc/13 - Vitamin C.mp3",
    "/home/jrha/Music/ReTagged/Jed Whedon/2008 - Dr. Horrible's Sing-Along Blog/01 - Horrible Theme.m4a",
    "/home/jrha/Music/ReTagged/Mattias IA Eklundh/Freak Guitar: The Road Less Traveled/20 - One-String Improvisation.mp3",
]

class Player:


    def __init__(self):
        self.index = 0
        self.trackinfo = ""

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Audio-Player")

        self.window.connect("destroy", gtk.main_quit, "WM destroy")
        self.window.connect("delete_event", self.close_application)
        self.window.connect("key_press_event", self.close_application)

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
    

    def close_application(self, widget, event, data=None):
        #Only exit if window is closed or Escape key is pressed
        if event.type == gtk.gdk.KEY_PRESS and gtk.gdk.keyval_name(event.keyval) != "Escape":
            return True
        else:
            gtk.main_quit()
            return False


    def play(self):
        filepath = songs[self.index]

        self.index += 1
        if self.index >= len(songs):
            self.index = 0

        if os.path.isfile(filepath):
            self.player.set_property("uri", "file://" + filepath)
            self.player.set_state(gst.STATE_PLAYING)
            #print("PLAYING: %s" % filepath)


    def stop(self):
            self.player.set_state(gst.STATE_NULL)


    def on_message(self, bus, message):
        t = message.type

        if t == gst.MESSAGE_EOS: # End Of Stream
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

                    #print("TRACKINFO: %s" % self.trackinfo)
                    self.label.set_label(self.trackinfo)




if __name__ == "__main__":
    p = Player()
    p.play()
    gtk.main()
