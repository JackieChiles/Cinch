#!/usr/bin/python3
"""
!Built for Initial Network Capability for handling Chat-like data, not game data.

Web server for game engine communication for Cinch (not for web pages).
To access, use the following code in a root-level module:
    import web.web_server as server
    server.start_server()

TODO:   Add send_error functionality
        Add logging
        Change Access-Control-Allow-Origin to appropriate resource
        See what happens if client closes connection while server is thinking

* Inspired by Voxound comet server

"""
from http.server import HTTPServer,BaseHTTPRequestHandler  
from socketserver import ThreadingMixIn
from threading import Lock, Event
from urllib.parse import urlparse
from cgi import escape
import json
from collections import deque

from . import web_config as settings


class CometServer(ThreadingMixIn, HTTPServer):
    """Perform event handling for comet long polling using many threads."""
    def __init__(self, hostname, port, cache_size=settings.CACHE_SIZE):
        """Initialize server. Overrides inherited __init__."""
        HTTPServer.__init__(self, (hostname, port), HttpHandler)

        self.max = cache_size
        self.lastid = 0
        self.queue = deque(maxlen=cache_size)
        self.events = []
        self.lock = Lock()

        self.listeners = []

    def run_server(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:   # Exit gracefully with CTRL^C
            print("Server halted with keyboard interrupt.\n")

    def add_announcer(self, channel):
        """

        """


    def add_listener(self, channel, signature=None):
        """Register listener for handling incoming data/requests.

        channel (CommChannel): external object that cares to handle messages
        signature (list): list of keys for JSON encoded dictionary of data
            that handler cares about

        """
        #do some error handling/assertion, since this gets used outside server
        #assert something
        if signature is None:
            signature = channel.signature
        
        self.listeners.append({"listener":channel, "signature":signature})

    def handle_event(self, msg):
        """Try to handle event with registered event handler.

        msg (dict): JSON encoded dictionary of message received by server

        """
        for h in self.listeners:
            if (all (k in msg for k in h["signature"]) and
                all (k in h["signature"] for k in msg)): #test for 1-to-1 mapping

                handler = h["listener"]  #really need to rework this naming
                try:
                    return handler.callback(msg)
                except Exception:
                    return None, None #make more useful

        return None, None

    def retrieve(self, lastid, timeout):
        """Retrieve all events from queue with lastid or later.

        lastid (int): last event id client was sent...
        timeout (float): seconds for thread to wait for new message;
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
                return (True, (lastid, msgs))

            #else listen for new event during timeout
            event = Event()
            self.events.append(event)

        # Current event queue empty, so wait for new message
        event.wait(timeout)
        if event.is_set():
            return (True, (self.lastid, [self.queue[-1]]))
        else:
            return (False, None)

    def notify(self, header, args):
        """Add new event to event queue.

        header (str/int): descriptor for kind of event -- not using ATM
        args (dict): JSON encoded argument/data list

        """
        msg = "[{0}, {1}]".format(header, json.dumps(args))

        # Enqueue message
        with self.lock:        #locks the thread, then unlocks at end of block
            self.lastid += 1
            self.queue.append(msg)

            # thread management?
            for event in self.events: #frees all events created by.notify
                event.set()
            self.events = []
        
  
class HttpHandler(BaseHTTPRequestHandler):
    """Handle GET/POST requests for Cinch from web clients."""
    def do_GET(self):
        """Process GET requests for Cinch application.

        Primarily used to push status updates to clients (via Comet), but
        able to handle other GET requests (to be determined). GET is to
        be read-only.

        """
        ## Acknowledge request
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain") # mime-type
        self.send_header("Access-Control-Allow-Origin", "*") #handle CORS
        self.end_headers()

        ## Interpret request
        parsed_path = urlparse(self.path)
        self.raw_query = parsed_path.query
        self.parse_data()
        #check for long-polling flag (in handler?)
        #add client to active client list; have routine for clients to stale out
        ## client logging shall be handled in a ... handler.

         ## Delegate data to appropriate engines
##        header, message = self.server.handle_event(self.json)
##        if message == None:
##            header = "error"
##            message = "no handler found!"
        ##work on default GET handling; maybe don't notify in unknown cases?
               


        ## here we are sending out the event queue to all once there are 2
        ## items in it.
        success, res = self.server.retrieve(self.server.lastid-1, 2.5)
        if success:
            idd, msgs = res
            self.send_message("{0}::{1} --- {2}".format(
                idd, self.server.lastid, json.dumps(msgs)))
        else:
            self.send_message("erk")

        #####
        # Do stuff if not a Comet GET
        #####
        
    def do_POST(self):
        """Process POST requests for Cinch application.

        Primarily used to handle Ajax requests -- game actions and chats.
        Input from POSTs are assumed to require evaluation by the server
        and will be parsed and passed to the appropriate engine.
        
        """
        ## Acknowledge request.
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*") #handle CORS
        self.end_headers()

        ## Interpret request.
        content_len = int(self.headers.__getitem__('content-length'))
        self.raw_query = self.rfile.read(content_len)
        self.parse_data()

        ## Delegate data to appropriate engines
        header, message = self.server.handle_event(self.json)
        if message == None:
            header = "error"
            message = "no handler found!"
        ##work on default POST handling; maybe don't notify in unknown cases?
##need to do stuff with ID number???
        self.server.notify(header, self.json)
        self.send_message(message)

    def parse_data(self):
        """Parse raw_query into dictionary."""
        try:
            self.query = self.raw_query.decode()    # convert bytes to str
        except AttributeError:
            self.query = self.raw_query             # input already a str
        finally:
            self.query = escape(self.query)         # sanitize inputs

        try:
            self.json = json.loads(self.query)
        except ValueError:
            self.json = {"Error":"Input not in JSON format"}

    def send_message(self, message):
        """Helper interface for sending data to client."""
        try:
            m = message.encode()
        except AttributeError:
            m = message

        self.wfile.write(m)


def boot_server():
    """Initialize server."""
    try:
        server = CometServer(settings.HOSTNAME, settings.PORT)
    except Exception:
        print("Error booting server.\n")
        return
    
    print("Server started on {0}, port {1}...".format(
        settings.HOSTNAME, settings.PORT))
    return server
