#!/usr/bin/python3
"""
Web server for game engine communication for Cinch (not for web pages).
To access, use the following code in a root-level module:
    import web.web_server as server
    server.start_server()

TODO:   Add send_error functionality
        Add logging
        Change Access-Control-Allow-Origin to appropriate resource

"""
from http.server import HTTPServer,BaseHTTPRequestHandler  
from socketserver import ThreadingMixIn
import threading

from urllib.parse import urlparse
from cgi import escape
import json

from . import web_config as settings


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
  
class HttpHandler(BaseHTTPRequestHandler):
    """Handle GET/POST requests for Cinch from web clients."""
    def do_GET(self):
        """Process GET requests for Cinch application."""
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain") # mime-type
        self.end_headers()

        parsed_path = urlparse(self.path)
        self.raw_query = parsed_path.query
        self.parse_data()

        ##test
        message = '\n'.join([
                'CLIENT VALUES:',
                'client_address=%s (%s)' % (self.client_address,
                                            self.address_string()),
                'command=%s' % self.command,
                'path=%s' % self.path,
                'real path=%s' % parsed_path.path,
                'query=%s' % parsed_path.query,
                'request_version=%s' % self.request_version,
                '',
                'SERVER VALUES:',
                'server_version=%s' % self.server_version,
                'sys_version=%s' % self.sys_version,
                'protocol_version=%s' % self.protocol_version,
                '\n\n',
                'thread ID=%s' % threading.currentThread().getName()
                ])

        self.send_message(message)

    def do_POST(self):
        """Process Ajax JSON POST requests for Cinch application."""
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*") #handle CORS
        self.end_headers()
        
        content_len = int(self.headers.__getitem__('content-length'))
        self.raw_query = self.rfile.read(content_len)
        self.parse_data()

        ##test
        keys = [x for x in self.json.keys()]
        vals = [x for x in self.json.values()]
        d = { vals[0] : keys[0] }
        message = json.dumps(d)
        ##
        
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


def start_server():
    """Initialize server."""
    httpd = ThreadedHTTPServer(
        (settings.HOSTNAME, settings.PORT), HttpHandler)
    print("Server started on {0}, port {1}..." .format(settings.HOSTNAME,
                                                       settings.PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:   # Exit gracefully with CTRL^C
        print("Server halted with keyboard interrupt.\n")
