#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  Copyright (C) 2013  James Adams
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

from time import sleep
from sys import stdout

from library import *

from prettytable import PrettyTable


def last_played(library):
    tracks = library.query(sspTrack).order_by(sspTrack.lastplayed.desc()).limit(50).all()
    fields = ["Last Played", "Artist", "Track"]
    table = PrettyTable(fields)

    for field in fields:
        table.set_field_align(field, "l")

    for track in tracks:
        filepath = track.filepath.split("/")
        table.add_row([track.lastplayed, filepath[-3], filepath[-1]])

    table.printt()


def unplay_last_played(library):
    track = library.query(sspTrack).order_by(sspTrack.lastplayed.desc()).first()
    print "Unplaying: %s" % (track.filepath)
    print "          plays:%d" % (track.playcount)
    print "          skips: %d" % (track.skipcount)
    print "    last played: %s" % (track.lastplayed)
    print
    print "This will only re-queue an accidentally played track, hourly play statistics will be unaffected."
    print "There will be a five second pause while you think about what you have done."
    for i in range(0, 5):
        stdout.write("%d..." % (5-i))
        stdout.flush()
        sleep(1)
    track.playcount -= 1
    track.lastplayed = None
    library.commit()
    print "DONE"


def most_skipped_artists(library):
    tracks = library.query(sspTrack.filepath).filter(sspTrack.skipcount >= 1).all()

    fields = ["Skips", "Artist"]
    table = PrettyTable(fields)

    for field in fields:
        table.set_field_align(field, "l")

    artists = {}

    for track in tracks:
        artist = track.filepath.split("/")[-3]
        if artist not in artists:
            artists[artist] = 0
        artists[artist] += 1

    artists = [ [s,a] for a,s in artists.iteritems() ]
    artists.sort(key = lambda record: record[1])
    artists.sort(key = lambda record: record[0])
    artists.reverse()

    for record in artists[:20]:
        table.add_row(record)

    table.printt()


def playthrough_progress(library):
    stats = library.query(func.count(sspTrack.playcount)).group_by(sspTrack.playcount).order_by(sspTrack.playcount.desc()).all()
    played = float(stats[0][0])
    unplayed = float(stats[1][0])
    print "Currently %.1f%% through current pass of library" % (played / (played + unplayed) * 100)


if __name__ == "__main__":
    library = connect()
    import argparse
    parser = argparse.ArgumentParser(description='Super Simple Player')
    parser.add_argument('info', choices=["last_played", "unplay_last_played", "most_skipped_artists", "playthrough_progress"], help="Which piece of information to display")
    args = parser.parse_args()

    if args.info == "last_played":
        last_played(library)
    elif args.info == "unplay_last_played":
        unplay_last_played(library)
    elif args.info == "most_skipped_artists":
        most_skipped_artists(library)
    elif args.info == "playthrough_progress":
        playthrough_progress(library)
