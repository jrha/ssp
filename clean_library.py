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

from os.path import exists

from library import *
from sqlalchemy.exc import IntegrityError

import argparse
parser = argparse.ArgumentParser(description='Super Simple Player - Library Cleaner - Scan library for tracks that are missing from disk and remove them, by default this will not remove tracks if they have ever been played.')
parser.add_argument('--dontignore', action="store_true", help="Don't ignore tracks that have been played when cleaning up")
args = parser.parse_args()
del parser

session = connect()
session.text_factory = str

for track in session.query(sspTrack):
    if not exists(track.filepath):
        if args.dontignore or track.playcount == 0:
            session.delete(track)
            print "REMOVED: %s" % (track.filepath)
        else:
            print "IGNORED: %s" % (track.filepath)

session.commit()
