#!/usr/bin/python3
"""
Comet web server for Cinch game engine communication with clients.

TODO:   
        Add logging
        Change Access-Control-Allow-Origin to appropriate resource

"""
from http.server import HTTPServer,BaseHTTPRequestHandler  
from socketserver import ThreadingMixIn
from threading import Lock, Event
from urllib.parse import urlparse, parse_qs
from cgi import escape
import json
from collections import defaultdict, deque

from web import web_config as config
from web.channel import CommChannel
from web.message import Message


class CometServer(ThreadingMixIn, HTTPServer):    
    """Perform event handling for comet long polling using many threads."""
    def __init__(self, hostname, port):
        """Initialize server. Overrides inherited HTTPServer __init__."""
        super(HTTPServer, self).__init__((hostname, port), HttpHandler)

        max_connections = config.MAX_CLIENTS
        cache_size = config.CACHE_SIZE

        # For each new request, create a deque
        self.handler_queue = deque(maxlen=max_connections)

        # Message buffer        
        self.message_queue = defaultdict(list)
        
        self.lock = Lock()    # Thread control for server
        self.responders = []  # List of CommChannels for handling POST queries

    ####################
    # Server-focused methods
    ####################

    def run_server(self):
        try:
            self.serve_forever()
        except KeyboardInterrupt:   # Exit gracefully
            # Release all handler threads so server doesn't wait for timeout
            hq = list(self.handler_queue)
            for h in hq:
                try:  h.event.set()
                except:  pass  # h may have exited on its own
                
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

    def matches_signature(self, channel, msg):
        """Determine if msg signature matches channel signature.

        channel (CommChannel): channel
        msg (Message): message

        returns: True or False

        """
        if (all (k in msg.data for k in channel['signature']) and
            all (k in channel['signature'] for k in msg.data)):
            return True

        else:
            return False
                
    def handle_msg(self, channel, msg):
        """Handle event with registered channel.

        msg is an incoming message which is handed to a channel for processing.

        channel (CommChannel): channel designated for handling this
            type of msg
        msg (Message): Message object message received by server

        return: Message response from channel, or None

        """
        assert isinstance(channel, CommChannel)
        assert isinstance(msg, Message)

        response = channel.respond(msg)

        assert (isinstance(response, (Message, dict)) or response is None)
        
        return response

    ####################
    # Client-focused methods
    ####################

    def capture_handler(self, http_handler):
        """Add http_handler to handler_queue and set event flags for later.
        
        Captures handler for later writing to by notify().
        
        http_handler (HttpHandler): request handler
        
        """
        # Check if handler for guid is already in queue. If so, close out all
        # old ones. Should only be at most one handler per guid, but loop just
        # in case.
        old_handler = self.retrieve_handler(http_handler.guid)
        while old_handler is not None:
            self.release_handler(old_handler)
            old_handler = self.retrieve_handler(http_handler.guid)    

        # If there are old messages in the queue, send them now
        output = self.get_old_messages(http_handler.guid)
        if len(output) > 0:
            # Return output for writing without further capture
            http_handler.send_message(output)
            return False

        else:
            # Set event() flag on handler
            http_handler.event = Event()
            http_handler.in_use = False
            
            # Add handler to list of active http handlers        
            self.handler_queue.append(http_handler)
            
            return True  # Do http_handler.event.wait() from calling method

    def retrieve_handler(self, guid):
        """Get active HttpHandler object for guid from handler_queue.

        guid (str): guid of client creating http request
        returns: HttpHandler, or None if no handler present for guid

        """
        my_handlers = [x for x in self.handler_queue if x.guid == guid]
        if len(my_handlers) > 0:
            return my_handlers[0] # Return first (oldest) handler in queue
        else:
            return None
        
    def get_old_messages(self, target):
        """Retrieve any messages for target from message_queue.

        target (str): guid of client

        """
        output = []

        if target in self.message_queue:
            # Get all message data from message_queue for target
            with self.lock:
                msgs = self.message_queue[target]
                output = [y.data for y in msgs]

                # Remove those messages from message_queue
                if len(msgs) > 0:
                    del self.message_queue[target]

        return output
        
    def notify(self, msg):
        """Attempt to match msg up with active handler.

        If cannot find active handler, push into queue for later delivery.

        msg (Message): Message object

        """
        assert isinstance(msg, Message)

        target = msg.target

        handler = self.retrieve_handler(target)
        if handler is not None:
            if handler.in_use is False:
                handler.in_use = True
                with self.lock:
                    # Gather any messages from queue for target, plus incoming msg
                    # (get_old_messages() will ususally return [])
                    output = self.get_old_messages(target)
                    output.append(msg.data)

                    handler.send_message(output)
                    handler.event.set() # Release wait()

            else: # Handler currently in use and will be closed when done
                self.message_queue[target].append(msg)

        else:  # No handler for msg, so add to queue for later delivery
            self.message_queue[target].append(msg)
            
    def release_handler(self, http_handler):
        """Release handler from handler_queue.

        http_handler (HttpHandler): request handler

        """
        try:  http_handler.event.set()
        except AttributeError:  pass  # Handler may not have been captured

        try:  self.handler_queue.remove(http_handler)
        except ValueError:  pass  # Handler may not have been enqueued
    

class HttpHandler(BaseHTTPRequestHandler):
    """Handle GET/POST requests for Cinch from web clients."""
    def do_GET(self):
        """Process GET requests for Cinch application.

        Exclusively used to send data from server/engine to requesting clients.
        Comet GET requests must have the following field:
        - uid: GUID of requesting client
        
        """
        # Parse request
        parsed_path = urlparse(self.path)
        self.parse_data(parsed_path.query)

        # Acknowledge request with status code and headers regardless of
        # content. This lets browser finish request cleanly.
        self.acknowledge_request()

        # If valid Comet request, capture handler for future notification
        if config.GUID_KEY in self.data:
            # Extract client guid from data
            self.guid = self.data[config.GUID_KEY]

            # Attempt to capture request and begin waiting
            if self.server.capture_handler(self):
                # You can store the result (True/False) from wait() if desired
                self.event.wait(config.COMET_TIMEOUT)

                # Shutdown handler
                self.server.release_handler(self)

        else: # Not a valid Comet request, so do nothing
            pass

    def do_POST(self):
        """Process POST requests for Cinch application.

        Primarily used to handle Ajax requests -- game actions and chats.
        Input from POSTs are assumed to require evaluation by the server
        and will be parsed and passed to the appropriate engine.

        """
        # Parse request
        content_len = int(self.headers['content-length'])
        self.parse_data(self.rfile.read(content_len).decode()) # Decode bytes

        # Acknowledge request with status code and headers regardless of
        # content. This lets browser finish request cleanly.
        self.acknowledge_request()       

        # Assemble message for engine. Initial entry msgs don't have guid.
        guid = self.data.get(config.GUID_KEY, None)

        # Strip guid info from data before building message
        if guid:  del self.data[config.GUID_KEY]
        
        msg = Message(self.data, source=guid)

        # If guid of POST is same as an active GET, close out GET to give
        # client a free connection -- HTTP best-practices: there should be no
        # more than 2 connections to a server from a single client. If the
        # client wants to spam POSTs, though, we won't stop it.
        if guid is not None:
            active_get_handler = self.server.retrieve_handler(guid)
            if active_get_handler is not None:
                active_get_handler.event.set()  # Close-out GET request now

        # Delegate data to appropriate channel; supports multiple channels
        channels = [x['channel'] for x in self.server.responders
                    if self.server.matches_signature(x, msg)]

        if len(channels) > 0:
            for channel in channels:
                response = self.server.handle_msg(channel, msg)

                if response is None:  # Most common case
                    pass
                elif isinstance(response, dict): 
                    self.send_message(response, mode="POST")

        else:
           # No handler exists, so print error message
            print("Warn: No handler for query: ", self.data)

    def acknowledge_request(self):
        """Send out status code and headers, common between GET and POST."""
        self.send_response(200)
        self.send_header(*config.CONTENT_TYPE)
        self.send_header(*config.ACCESS_CONTROL)
        self.end_headers()

    def log_request(self, code="-", size="-"):
        """Silence server output from GET/POST requests.

        Overriden from BaseHTTPHandler.
        
        """
        if self.requestline.startswith(("GET", "POST")):
            return
        else:
            super().log_request(code, size)

    def parse_data(self, data):
        """Parse raw request data into dictionary."""
        assert isinstance(data, str)
        
        query = escape(data)  # Sanitize inputs

        try:
            data = parse_qs(query)

            # parse_qs() wraps dict values in a list, so unpack them
            for k in data:  data[k] = data[k][0]

        except:
            data = {"Error": "Cannot parse data."}

        finally:
            self.data = data
                
    def send_message(self, data, mode="GET"):
        """Helper method for sending JSON-encoded data to client.

        data (dict): outgoing message set

        """
        # Repackage data for Comet requests
        if mode == "GET":
            data = {config.COMET_MESSAGE_BLOCK_KEY: data}
 
        output = json.dumps(data)
        try:
            self.wfile.write(output.encode())
        except ValueError:
            #this line is being monitored; may have been fixed with Issue #86
            print("ERROR IN LINE 371 OF WEB_SERVER.PY")
            raise


def boot_server():
    """Initialize server."""
    try:
        server = CometServer(config.HOSTNAME, config.PORT)
    except:
        print("Error booting server.\n")
        raise
    
    print("Server started.")
    print("Suppressing GET/POST output.")
    return server
