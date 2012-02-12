#!/usr/bin/python3
"""
!Built for Initial Network Capability for handling Chat-like data, not game data.

Web server for game engine communication for Cinch (not for web pages).

TODO:   Add send_error functionality
        Add logging
        Change Access-Control-Allow-Origin to appropriate resource
        See what happens if client closes connection while server is thinking
        Client management using HTML5 WebStorage

* Inspired by Voxound comet server

"""
from http.server import HTTPServer,BaseHTTPRequestHandler  
from socketserver import ThreadingMixIn
from threading import Lock, Event
from urllib.parse import urlparse, parse_qs
from cgi import escape
import json
from collections import deque

from web import web_config as config
from web.channel import CommChannel
from web.message import Message


class CometServer(ThreadingMixIn, HTTPServer):    
    """Perform event handling for comet long polling using many threads."""
    def __init__(self, hostname, port, cache_size=config.CACHE_SIZE):
        """Initialize server. Overrides inherited __init__."""
        HTTPServer.__init__(self, (hostname, port), HttpHandler)

        self.max = cache_size
        self.lastid = 0
        self.queue = deque(maxlen=cache_size)
        self.events = []    #temp list of threads when many hit server at once
        self.lock = Lock()  #thread control
        self.responders = []

    def run_server(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:   # Exit gracefully with CTRL^C
            print("Server halted with keyboard interrupt.\n")

    def add_announcer(self, channel):
        """Register channel as an announcer to the server.

        Announcer channel will call server's notify function when it needs
        to publish a message to the server. add_announcer() will give the
        channel a reference to the server's notify function.

        channel (CommChannel): object doing the announcing

        """
        assert isinstance(channel, CommChannel)

        # Create function for channel to call to server
        def handler(msg):
            assert isinstance(msg, Message)
            self.notify(msg)
            
        channel.add_announce_callback(handler)

    def add_responder(self, channel, signature):
        """Register responser for handling incoming data/requests.

        channel (CommChannel): external object that cares to handle messages
        signature (list): list of keys for JSON encoded dictionary of data
            that handler cares about

        """
        assert isinstance(channel, CommChannel)
        assert isinstance(signature, list)
        
        self.responders.append({'channel':channel, 'signature':signature})

    def filter_msgs(self, guid, msgs):
        """Filter out all Messages in msgs not intended for user guid.
        
        guid: guid value of client requesting message block
        msgs (list): block of candidate messages to be sent out

        """
        tmp = []
        for msg in msgs:
            if guid in msg.dest_list:
                tmp.append(msg)

        return tmp

    def get_responder(self, msg):
        """Checks server for registered response channel for msg.

        msg_data (dict or Message): incoming message data
        returns: channel if exists, None if not

        """
        assert isinstance(msg, (dict, Message))

        if isinstance(msg, Message):
            msg_data = msg.data
        else:
            msg_data = msg

        for r in self.responders:
            if (all (k in msg_data for k in r['signature']) and
                all (k in r['signature'] for k in msg_data)):

                return r['channel']

        return None
                
    def handle_msg(self, channel, msg):
        """Handle event with registered channel.

        channel (CommChannel): channel identified by exists_channel that
            is designated for handling this type of msg
        msg (Message): Message object message received by server
        return: Message response from channel, or None

        """
        assert isinstance(channel, CommChannel)
        assert isinstance(msg, Message)

        response = channel.respond(msg)

        assert (isinstance(response, Message) or response is None)
        
        return response

    def retrieve(self, lastid, timeout):
        """Retrieve all events from queue with lastid or later.

        lastid (int): last message id client had previously received
        timeout (float): time (in seconds) for thread to wait for new message;
            must be shorter than client-side AJAX timeout.

        """
        with self.lock:
            #if events have occured since lastid, then get those events
            if lastid >= 0 and lastid < self.lastid:
                interval = self.lastid - lastid
                if interval > self.max:
                    interval = self.max

                msgs = list(self.queue[interval*-1 + x] for
                            x in range(interval))
                return (True, (self.lastid, msgs))

            #else listen for new event during timeout
            event = Event()
            self.events.append(event)

        # Current event queue empty, so wait for new message
        event.wait(timeout)
        if event.is_set():
            return (True, (self.lastid, [self.queue[-1]]))
        else:
            return (False, None)

    def notify(self, msg):
        """Add new message to queue.

        msg (Message): Message object containing source/dest/data.

        """
        assert isinstance(msg, Message)

        # Enqueue message
        with self.lock:        #locks the thread, then unlocks at end of block
            self.lastid += 1
            self.queue.append(msg)

            # thread management
            for event in self.events: #frees all events created by notify
                event.set()
            self.events = []

  
class HttpHandler(BaseHTTPRequestHandler):
    """Handle GET/POST requests for Cinch from web clients."""
    def do_GET(self):
        """Process GET requests for Cinch application.

        Exclusively used to send items from server.queue to requesting clients.
        Comet GET requests must have the following fields:
        - uid: GUID of requesting client
        - last: # of last message received (-1 if no messages received yet)
        
        """
        ## Interpret request
        parsed_path = urlparse(self.path)
        self.raw_query = parsed_path.query  #reevaluate this flow
        self.parse_data()
        message = Message(self.json, source_key=config.GUID_KEY)
        
        ## Acknowledge request
        self.send_response(config.OK_RESPONSE)
        self.send_header(*config.CONTENT_TYPE)
        self.send_header(*config.ACCESS_CONTROL) #handle CORS
        self.end_headers()

        client_lastid = message.data.get(config.COMET_LAST_MSG_KEY, None)
        if (client_lastid is None) or (message.source is None):
            # GET is not valid Comet query
            print("not a valid Comet query")
            return  #or other option for non-Comet GETs
        else:
            client_lastid = int(client_lastid)
            
        success, res = self.server.retrieve(client_lastid,
                                            config.COMET_TIMEOUT)
        if success:
            server_lastid, msgs = res

            # Filter messages based on Message recipient list, requestor
            guid = message.source
            msgs = self.server.filter_msgs(message.source, msgs)
            # Return if no messages remain after filtering
            if len(msgs) == 0:
                return
            
            # Stringify message block
            msgs_data = []
            for msg in msgs:
                msgs_data.append(msg.data)

            self.send_message({config.COMET_LATEST_KEY: server_lastid,
                               config.COMET_MESSAGE_BLOCK_KEY: msgs_data})

    def do_POST(self):
        """Process POST requests for Cinch application.

        Primarily used to handle Ajax requests -- game actions and chats.
        Input from POSTs are assumed to require evaluation by the server
        and will be parsed and passed to the appropriate engine.
        
        """
        ## Interpret request.
        content_len = int(self.headers['content-length'])
        self.raw_query = self.rfile.read(content_len)
        self.parse_data()
        message = Message(self.json, source_key=config.GUID_KEY)
        
        ## Acknowledge request.
        self.send_response(config.OK_RESPONSE)
        self.send_header(*config.CONTENT_TYPE)
        self.send_header(*config.ACCESS_CONTROL)
        self.end_headers()

        ## Delegate data to appropriate sinks.
        channel = self.server.get_responder(message)
        if channel is None:
            # No handler exists, so print error message
            print("Warn: No handler for query: ", self.json)
        else:
            response = self.server.handle_msg(channel, message)

            if isinstance(response, Message): # e.g. error states, new game
                self.send_message(response.data)

    def parse_data(self):
        """Parse raw_query into dictionary."""
        try:
            query = self.raw_query.decode()     # convert bytes to str
        except AttributeError:
            query = self.raw_query              # input already a str
        finally:
            query = escape(query)               # sanitize inputs

        try:
            self.json = json.loads(query)
        except ValueError:
            # Data may be from GET query
            try:
                self.json = parse_qs(query) #query is (likely) from GET
                # GET values get packed into lists by parse_qs, while we
                # expect a single value per key. Unpack the "lists".
                for k in self.json:
                    self.json[k] = self.json[k][0]
            except Exception:
                self.json = {"Error": "Cannot parse data."}

    def send_message(self, message):
        """Helper interface for sending data to client."""
        assert isinstance(message, (str, bytes, dict))

        if isinstance(message, dict):
            message = json.dumps(message)
        
        try:
            m = message.encode()
        except AttributeError:
            m = message

        self.wfile.write(m)


def boot_server():
    """Initialize server."""
    try:
        server = CometServer(config.HOSTNAME, config.PORT)
    except Exception:
        print("Error booting server.\n")
        return
    
    print("Server started on {0}, port {1}...".format(
        config.HOSTNAME, config.PORT))
    return server
