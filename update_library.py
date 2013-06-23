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

import os
import mimetypes


from library import *
from sqlalchemy.exc import IntegrityError

mimetypes.init()

import argparse
parser = argparse.ArgumentParser(description='Super Simple Player - Library Updater')
parser.add_argument('path', help="Path of the root of your music collection")
parser.add_argument('--verbose', action="store_true", help="Print track info, even when a track already exists in the library")
args = parser.parse_args()
del parser

session = connect()
session.text_factory = str

if args.path:
    for root, dirs, files in os.walk(args.path):
        for f in files:
            filepath = "%s/%s" % (root.decode('utf8'), f.decode('utf8'))
            mimetype = mimetypes.guess_type(filepath)

            if type(mimetype) is tuple:
                mimetype = mimetype[0]

            if mimetype and "audio" in mimetype:
                try:
                    session.add(sspTrack(filepath))
                    session.commit()
                    print "ADDED: %s" % (filepath.encode('utf8'))
                except IntegrityError:
                    if args.verbose:
                        print "EXISTS: %s" % (filepath.encode('utf8'))
                    session.rollback()
