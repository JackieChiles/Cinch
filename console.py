#!/usr/bin/python2
"""Command console for Cinch server.

Requires socketIO-client package, available here:
https://github.com/invisibleroads/socketIO-client

This package will also support the AI program.

"""

import curses
import curses.textpad
import threading
from time import sleep
from socketIO_client import SocketIO, BaseNamespace


class Namespace(BaseNamespace):

    def __init__(self, *args):
        super(Namespace, self).__init__(*args)
        self.window = None # Must connect a screen!

    #------------------------#
    # Console Logging Method #
    #------------------------#

    def log_to_console(self, log_string):
        c_y, c_x = self.window.getyx()
        self.window.scroll(1)
        self.window.move(self.window.getmaxyx()[0] - 2, 0)
        self.window.insertln()
        self.window.addstr(log_string)
        self.window.move(c_y, c_x + 1) # Kludgy temp hack to move cursor to prompt.
        self.window.refresh()

    #----------------#
    # Event Handlers #
    #----------------#

    def on_ackNickname(self, *args):
        resp_line = 'New nickname: '
        for x in args:
            resp_line += x
        self.log_to_console(resp_line)

    def on_connect(self):
        self.log_to_console('[Connected]')

    def on_err(self, *args):
        resp_line = ''
        for err_text in args:
            resp_line += err_text
        self.log_to_console(resp_line)

    def on_rooms(self, room_list):
        resp_line = "Rooms: "
        for r in room_list:
            resp_line += r
        self.log_to_console(resp_line)

    #-------------------#
    # Callback Handlers #
    #-------------------#

    def cmd_response(*args):
        resp_line = ''
        for x in args:
            resp_line += x
        self.log_to_console(resp_line)

    def null_response(self, *args):
        pass

def listen_to_server(socket):
    # When opened in a thread separate from the graphical console, allows
    # continuous updates from the server to be processed in real-time.
    while True:
        socket.wait_for_callbacks(seconds=1)

def console(scr): # Put optional custom connection info here later?

    # Enable scrolling of command window
    scr.scrollok(True)

    # Define command prompt
    PROMPT_STR = "cinch>"

    # Establish connection
    socket = SocketIO('localhost', 8088)
    listener = threading.Thread(target=listen_to_server, args=(socket,))
    listener.daemon = True
    listener.start()
    ns = socket.define(Namespace, '/cinch')
    ns.window = scr

    # Test & initialize connection
    sleep(0.5)
    ns.emit('test', 'console', callback=ns.null_response)
    
    # Create the command line window:
    cmdline = curses.newwin(1, scr.getmaxyx()[1] - 7, scr.getmaxyx()[0]-1, 7)
    cmdprompt = curses.textpad.Textbox(cmdline)
    cmd = '' # Initialize cmd.
    scr.addstr(scr.getmaxyx()[0] - 1, 0, PROMPT_STR)
    cmdline.move(0, 0)
    scr.refresh()

    # Run the console.
    while True:

        # Await next command.
        cmd = cmdprompt.edit()

        # Update the window.
        scr.scroll(1)
        scr.addstr(scr.getmaxyx()[0] - 2, 7, cmd)
        scr.addstr(scr.getmaxyx()[0] - 1, 0, PROMPT_STR)
        scr.refresh()
        cmdline.erase()
        cmdline.move(0, 0)
        cmdline.refresh()

        # Process the command.
        if cmd.startswith('test'):
            ns.emit('test', 'console', callback=ns.null_response)
        elif cmd.startswith('nick '):
            ns.emit('nickname', cmd[5:])
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass
        elif cmd.startswith(''):
            pass

    # Disconnect
    socket.disconnect()
    
#----------------#
# Curses Wrapper #
#----------------#

curses.wrapper(console)

# Need to detect server-side if the client closes the connection.
