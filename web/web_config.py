#!/usr/bin/python3
"""
Configuration settings for server.py.
"""
HOSTNAME = "localhost"
PORT = 2424        # integer

# HTTP Header constants
OK_RESPONSE = 200
CONTENT_TYPE = ("Content-type", "text/plain")
ACCESS_CONTROL = ("Access-Control-Allow-Origin", "*")   #handle CORS

CACHE_SIZE = 5    # num of actions to hold in queue

GUID_KEY = 'uid'

## Web server data keys

# Key sent by client for id of last received message
COMET_LAST_MSG_KEY = 'last'
COMET_LATEST_KEY = 'new'
COMET_MESSAGE_BLOCK_KEY = 'msgs'

COMET_TIMEOUT = 2.5     #seconds
