#!/usr/bin/python3
"""
Web server for game engine communication for Cinch (not for web pages).
To access, use the following code in a root-level module:
    import web.web_server as server
    server.start_server()
"""
from http.server import HTTPServer,BaseHTTPRequestHandler  
from socketserver import ThreadingMixIn
import threading

from urllib.parse import parse_qs, urlparse
from html import escape
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

        self.query = self.path[2:]   #trim '/?' from path (=query)
        self.parse_data()

        ##test
        parsed_path = urlparse(self.path)
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

        self.wfile.write(message.encode())  #convert str to bytearray
        return

    def do_POST(self):
        """Process POST requests for Cinch application."""
        self.send_response(settings.OK_RESPONSE)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        
        content_len = int(self.headers.__getitem__('content-length'))
        self.query = self.rfile.read(content_len).decode('utf-8') #decode bytes
        self.parse_data()

        ##test
        message = "\n You sent a POST request with parameters {0}".format(
            json.dumps(self.fields))

        self.wfile.write(message.encode())  #convert str  to bytearray
        return

    def parse_data(self):
        """Break-out query data into dictionary, self.fields."""
        #convert self.query to string using try-except block here, instead of
        #in the GET/POST functions.
        clean_data = escape(self.query)  #sanitize inputs
        self.fields = parse_qs(clean_data)
        print(self.fields)
        return


def start_server():
    httpd = ThreadedHTTPServer(
        (settings.HOSTNAME, settings.PORT), HttpHandler)
    print("Server started on {0}, port {1}..." .format(settings.HOSTNAME,
                                                       settings.PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:   # Exit gracefully with CTRL^C
        print("Server halted with keyboard interrupt.\n")


if __name__ == '__main__':
    start_server()
