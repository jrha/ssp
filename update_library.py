#!/usr/bin/python
# coding=utf8

import os
import mimetypes

from library import *

mimetypes.init()

import argparse
parser = argparse.ArgumentParser(description='Super Simple Player - Library Updater')
parser.add_argument('path', help="Path of the root of your music collection")
args = parser.parse_args()
del parser

session = connect()

if args.path:
    for root, dirs, files in os.walk(args.path):
        for f in files:
            filepath = "%s/%s" % (root, f)
            mimetype = mimetypes.guess_type(filepath)

            if type(mimetype) is tuple:
                mimetype = mimetype[0]

            if mimetype and "audio" in mimetype:
                session.add(sspTrack(filepath))

session.commit()
