#!/usr/bin/python
# coding=utf8

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
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


def connect():
    base_path = dirname(argv[0])
    engine = create_engine('sqlite:///%s/library.db' % base_path, echo=False)

    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)

    return(Session())
