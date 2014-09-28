#!/usr/bin/env python
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
import web
import calendar

from library import *

URLS = (
    '/(.*)', 'info',
)

PAGES = [
    'last_played',
    'most_skipped_artists',
    'playthrough_progress',
    'unplay_last_played',
    'stats',
]

render = web.template.render('templates', globals = {'type' : type})

def navbar(page):
    result = []
    for p in PAGES:
        active = ''
        if p == page:
            active = ' class="active"'
        result.append('<li%s><a href="%s">%s</a></li>' % (active, p, p.replace('_', ' ').title()))
    return "\n".join(result)


def pageify(page, content):
    nav = navbar(page)
    title = page.replace('_', ' ').title()
    return render.index(nav, title, content)


class info():
    def GET(self, name):
        if name == "last_played":
            return last_played()
        elif name == "unplay_last_played":
            return unplay_last_played()
        elif name == "most_skipped_artists":
            return most_skipped_artists()
        elif name == "playthrough_progress":
            return playthrough_progress()
        elif name == "stats":
            return stats()
        else:
            return home()


def home():
    library = connect()
    return pageify(
        'Super Simple Player',
        [
            'Schema Version %s' % SCHEMA_VERSION,
            '%d tracks in library' % library.query(sspTrack).count(),
        ]
    )


def last_played():
    library = connect()
    tracks = library.query(sspTrack).order_by(sspTrack.lastplayed.desc()).limit(50).all()
    fields = ["Last Played", "Artist", "Track"]
    table = []

    for track in tracks:
        filepath = track.filepath.split("/")
        table.append([track.lastplayed, filepath[-3], filepath[-1]])

    return render.table(navbar("last_played"), "Last Played", fields, table)


def unplay_last_played():
    library = connect()
    track = library.query(sspTrack).order_by(sspTrack.lastplayed.desc()).first()

    return render.unplay_last_played(navbar('unplay_last_played'), track.filepath, track.playcount, track.skipcount, track.lastplayed)
    #for i in range(0, 5):
    #    stdout.write("%d..." % (5-i))
    #    stdout.flush()
    #    sleep(1)
    #track.playcount -= 1
    #track.lastplayed = None
    #library.commit()
    #print "DONE"


def most_skipped_artists():
    library = connect()
    tracks = library.query(sspTrack.filepath).filter(sspTrack.skipcount >= 1).all()

    fields = ["Skips", "Artist"]
    table = []

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
        table.append(record)

    return render.table(navbar("most_skipped_artists"), "Most Skipped Artists", fields, table)


def playthrough_progress():
    library = connect()
    stats = library.query(func.count(sspTrack.playcount)).group_by(sspTrack.playcount).order_by(sspTrack.playcount.desc()).all()
    played = float(stats[0][0])
    unplayed = float(stats[1][0])
    perc = '%.1f%%' % (played / (played + unplayed) * 100)
    return render.playthrough_progress(navbar('playthrough_progress'), perc)


def stats():
    library = connect()
    rawstats = library.query(sspStat).all()

    limit = float(max(
        max([s.playcount for s in rawstats]),
        max([s.skipcount for s in rawstats])
    ))

    stats = []

    for s in rawstats:
        stats.append(
            (
                '%.2d - %.2d' % (s.hour, s.hour+1),
                '%.1f%%' % (50 - (s.skipcount / limit) * 50),
                '%.1f%%' % ((s.skipcount / limit) * 50),
                '%.1f%%' % ((s.playcount / limit) * 50),
                s.skipcount,
                s.playcount,
            )
        )


    weekgrid = [ [ ('rgb(255, 255, 255);', 0, 0) for h in range(0, 24) ] for d in range(0, 7) ]
    weekstats = library.query(sspWeekStat).all()
    weekmax = float(library.query(func.max(func.max(sspWeekStat.skipcount, sspWeekStat.playcount))).first()[0])

    for s in weekstats:
        rSkips = float(s.skipcount) / weekmax
        rPlays = float(s.playcount) / weekmax

        r = 255 - (255 * rPlays)
        b = 255 - (255 * rSkips)
        g = (r + b) / 2

        weekgrid[s.day][s.hour] = ("rgb(%d, %d, %d);" % (r, g, b), s.playcount, s.skipcount)

    return render.stats(navbar('stats'), stats, weekgrid, calendar.day_abbr)


if __name__ == "__main__":
    app = web.application(URLS, globals())
    app.run()
