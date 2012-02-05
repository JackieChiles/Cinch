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
        Client management using cookies

* Inspired by Voxound comet server

"""
from http.server import HTTPServer,BaseHTTPRequestHandler  
from socketserver import ThreadingMixIn
from threading import Lock, Event
from urllib.parse import urlparse
from cgi import escape
import json
from collections import deque

from web import web_config as settings
from web.channel import CommChannel

##class ClientManager:
##    """Provide management functions for client monitoring.
##
##    Setting/reading cookies...
##
##    """
##    def __init__(self):
##        clients = list()
##    
##    def add_client(self):
##        """Creates new client in client table.
##
##        Returns new client id, client guid.
##        """
##        return 3, "kittens"
##
##    def get_client(self, handler):
##        print("getting client...")
##        print(handler.headers)
##        ck = handler.headers['cookie']
##        return ck

  
##class CometServer(ThreadingMixIn, HTTPServer, ClientManager):
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

        self.responders = []

##        self.client_manager = ClientManager()

    def run_server(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:   # Exit gracefully with CTRL^C
            print("Server halted with keyboard interrupt.\n")

    def add_announcer(self, header, channel):
        """Register channel as an announcer to the server.

        Announcer channel will call server's notify function when it needs
        to publish a message to the server. add_announcer() will give the
        channel a reference to the server's notify function.

        header (str): descriptor word for messages announced by channel
        channel (CommChannel): object doing the announcing

        """
        assert isinstance(header, str)
        assert isinstance(channel, CommChannel)

        # Create function for channel to call to server
        def handler(*args): self.notify(header, args)
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

    def handle_msg(self, channel, msg):
        """Try to handle event with registered channel.

        channel (CommChannel): channel identified by exists_channel that
            is designated for handling this type of msg
        msg (dict): JSON encoded dictionary of message received by server
        return: msg-like response from channel

        """
        assert isinstance(channel, CommChannel)
        assert isinstance(msg, dict)

        response = channel.respond(msg)
        assert isinstance(response, dict)
        
        return response

    def get_responder(self, msg):
        """Checks server for registered responder for msg.

        msg (dict): incoming message
        returns: responder if exists, None if not

        """
        assert isinstance(msg, dict)

        for r in self.responders:
            if (all (k in msg for k in r['signature']) and
                all (k in r['signature'] for k in msg)):

                return r['channel']

        return None

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

            # thread management
            for event in self.events: #frees all events created by notify
                event.set()
            self.events = []

  
class HttpHandler(BaseHTTPRequestHandler):
    """Handle GET/POST requests for Cinch from web clients."""
    def do_GET(self):
        """Process GET requests for Cinch application.

        Exclusively used to send items from server.queue to requesting clients.
        GET requests must have the following fields:
        - id: id # of last message received (-1 for first message???)
        
        """
        ## Identify client


        ## Interpret request
        parsed_path = urlparse(self.path)
        self.raw_query = parsed_path.query
        self.parse_data()

        ## Acknowledge request
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain") # mime-type
        self.send_header("Access-Control-Allow-Origin", "*") #handle CORS
        self.end_headers()
      
        client_lastid = self.json.get('id', None)
        if client_lastid is None:  #GET is not valid Comet query
            #return  #or other option for non-Comet GETs
            client_lastid = self.server.lastid-1 #debug
        
        success, res = self.server.retrieve(client_lastid, 2.5)
        if success:
            server_lastid, msgs = res
            self.send_message("{{ id: {0}, msgs: {1} }}".format(
                server_lastid, json.dumps(msgs)))
        else:
            self.send_message("Nothing to report.\n")
       
    def do_POST(self):
        """Process POST requests for Cinch application.

        Primarily used to handle Ajax requests -- game actions and chats.
        Input from POSTs are assumed to require evaluation by the server
        and will be parsed and passed to the appropriate engine.
        
        """
        ## Identify client.
        ##need to do stuff with client ID???
        ### id will (probably) be a field in every message
        
        ## Acknowledge request.
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*") #handle CORS
        self.end_headers()

        ## Interpret request.
        content_len = int(self.headers['content-length'])
        self.raw_query = self.rfile.read(content_len)
        self.parse_data()

        ## Delegate data to appropriate sinks.
        channel = self.server.get_responder(self.json)
        if channel is None:
            #no handler exists, do default action
            self.server.notify('UNKNOWN', self.json)
        else:
            response = self.server.handle_msg(channel, self.json)
            self.send_message(response)
            ##let responders broadcast as they see fit
            ##will be implementing address/addressee functionality

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
