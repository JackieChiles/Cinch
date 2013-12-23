#!/usr/bin/python2
"""Command console for Cinch server.

Requires socketIO-client package, available here:
https://github.com/invisibleroads/socketIO-client

This package will also support the AI program.

"""
from time import sleep
from socketIO_client import SocketIO, BaseNamespace


class Namespace(BaseNamespace):

    def __init__(self, *args):
        super(Namespace, self).__init__(*args)

        self.on('do_response', self.on_do_response)

    def on_connect(self):
        print '[Connected]'

    # Need to implement ACL server-side so can run exec
    def cmd(self, msg):
        # Pass arbitrary python command to server
        self.emit('exec', msg)

    def on_do_response(*args):
        print 'do: ', args


# Establish connection
socketIO = SocketIO('localhost', 8088)
ns = socketIO.define(Namespace, '/cinch')
sleep(0.5)

# Display main menu
cmd = ''
while cmd != 'quit':
    print 'input command or type "help"'
    cmd = raw_input()

    # Process command
    if cmd.startswith('help'):
        print 'docstring!'
    elif cmd.startswith('do'):
        ns.cmd(cmd[3:])
    else:
        print 'try something else'

# Disconnect
socketIO.disconnect()
