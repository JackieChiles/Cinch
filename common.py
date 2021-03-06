#!/usr/bin/python2
"""Non-module specific items useful to all components."""


from datetime import datetime


SOCKETIO_PORT = 8088
SOCKETIO_NS = '/cinch'


# Construct sqlite database
from db.dal import DAL, Field

db = DAL('sqlite://storage.sqlite',folder='db')

# Database table definitions -- defined here rather than in the relevant
# modules to allow for reference fields without worrying about the import sequence.
db.define_table(
    'Games',
    Field('Timestamp', 'string', required=True),
    Field('PlayerName0', 'string', required=True),
    Field('PlayerName1', 'string', required=True),
    Field('PlayerName2', 'string', required=True),
    Field('PlayerName3', 'string', required=True),
)
db.define_table(
    'Events',
    Field('game_id', 'reference Games', required=True),
    Field('HandNumber', 'integer', required=True),
    Field('Timestamp', 'string', required=True),
    Field('EventString', 'text', required=True)
)
db.define_table(
    'hands',
    Field('game_id', 'reference Games', required=True),
    Field('dealer', 'integer'),
    Field('declarer', 'integer'),
    Field('trump', 'integer'),
    Field('high_bid', 'integer'),
    Field('hand_number', 'integer')
)
db.define_table(
    'actions',
    Field('game_id', 'reference Games', required=True),
    Field('hand_id', 'reference hands', required=True),
    Field('pnum', 'integer', required=True),
    Field('bid', 'integer'),
    Field('rank', 'integer'),
    Field('suit', 'integer')
)


def enum(**enums):
    """Create enum-type object. Create as: Numbers=enum(ONE=1, TWO=2)"""
    return type('Enum', (), enums)
