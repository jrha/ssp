#!/usr/bin/python
# coding=utf8

import os
import mimetypes

from library import *

mimetypes.init()

session = connect()

TOP = u"/home/media/audio/ReTagged/"

for root, dirs, files in os.walk(TOP):
  for f in files:
      filepath = "%s/%s" % (root, f)
      mimetype = mimetypes.guess_type(filepath)
      if type(mimetype) is tuple:
          mimetype = mimetype[0]
      if mimetype and "audio" in mimetype:
          #print("+ %-20s%s " % (mimetype, filepath))
          session.add(sspTrack(filepath))
      #else:
          #print("  %-20s%s" % (mimetype, filepath))

session.commit()
