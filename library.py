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


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql.expression import func
from datetime import datetime
from os.path import dirname
from sys import argv

Base = declarative_base()

class sspTrack(Base):
    __tablename__ = 'tracks'
    filepath = Column(String(512), primary_key=True)
    playcount = Column(Integer())
    skipcount = Column(Integer())
    lastplayed = Column(DateTime())

    def __init__(self, filepath):
        self.filepath = filepath
        self.playcount = 0
        self.skipcount = 0
        self.lastplayed = None

    def __repr__(self):
        return "<Track (%s - %s plays, %s skips, last played %s)>" % (self.filepath, self.playcount, self.skipcount, self.lastplayed)

class sspStat(Base):
    __tablename__ = 'stats'
    hour = Column(Integer(24), primary_key=True)
    playcount = Column(Integer())
    skipcount = Column(Integer())

    def __init__(self, hour):
        if hour > 0 and hour < 24:
            self.hour = hour
            self.playcount = 0
            self.skipcount = 0

    def __repr__(self):
        return "<Stat (Hour %s - %s plays, %s skips)>" % (self.hour, self. playcount, self.skipcount)


def connect():
    base_path = dirname(argv[0])
    engine = create_engine('sqlite:///%s/library.db' % base_path, echo=False)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return(Session())
