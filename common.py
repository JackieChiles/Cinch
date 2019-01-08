#!/usr/bin/python2
"""Non-module specific items useful to all components."""


from datetime import datetime


SOCKETIO_PORT = 8088
SOCKETIO_NS = '/cinch'


def enum(**enums):
    """Create enum-type object. Create as: Numbers=enum(ONE=1, TWO=2)"""
    return type('Enum', (), enums)
