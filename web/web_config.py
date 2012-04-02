#!/usr/bin/python3
"""
Configuration settings for web_server.py.
"""
HOSTNAME = ""
PORT = 2424        # integer

# HTTP Header constants
OK_RESPONSE = 200
CONTENT_TYPE = ("Content-type", "text/plain")
ACCESS_CONTROL = ("Access-Control-Allow-Origin", "*")   #handle CORS

MAX_CLIENTS = 128  # maximum number of simultaneous connections
CACHE_SIZE = 64    # maximum number of messages to store in queue

## Web server data keys

# Key sent by client for id of last received message
GUID_KEY = 'uid'
COMET_MESSAGE_BLOCK_KEY = 'msgs'

COMET_TIMEOUT = 10     # seconds to have Comet request wait for data
