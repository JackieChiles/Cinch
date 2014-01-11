#!/usr/bin/python2
# coding=UTF-8
"""Curses interface for Cinch console."""

# currently being used for debugging.

DESC = "Cinch console curses interface class, along with driver for same."

import curses
import curses.textpad

import locale
locale.setlocale(locale.LC_ALL,"")

import threading
from time import sleep

from textwrap import TextWrapper

import argparse
import logging
log = logging.getLogger(__name__)
LOG_SHORT ={'d':'DEBUG', 'i':'INFO', 'w':'WARNING', 'e':'ERROR', 'c':'CRITICAL'}

class CinchScreen():
    def __init__(self, main_win):
        self.main_win = main_win        
        self.ym, self.xm = self.getsizes()
        self.PROMPT = "cinch> "
        self.textwrapper = TextWrapper(width = self.xm) # used in write()
        self.cmd = '' # User input command; starts blank.

        # Define sub-window dimensions here.
        
        # First define the functional layout.
        self.DASHBOARD_HEIGHT = 10
        self.COMMAND_HEIGHT = 1
        self.TABLE_WIDTH = 25
        self.HAND_WIDTH = 12
        self.INFO_WIDTH = 30

        # Now derive the newwin() calls for each window.
        # 'h': height; 'w': width; 'y','x': y-x coord of top left corner

        cml = {'h':self.COMMAND_HEIGHT, 'w':self.xm - len(self.PROMPT),
               'y':self.ym - self.DASHBOARD_HEIGHT - self.COMMAND_HEIGHT,
               'x':len(self.PROMPT) }
        cpt = {'h':self.COMMAND_HEIGHT, 'w':len(self.PROMPT) + 1, 'y':cml['y'],
               'x':0}
        tw = {'h':cpt['y'], 'w':self.xm, 'y':0, 'x':0}
        tbl = {'h':self.DASHBOARD_HEIGHT, 'w':self.TABLE_WIDTH,
               'y':self.ym - self.DASHBOARD_HEIGHT, 'x':0}
        hnd = {'h':self.DASHBOARD_HEIGHT, 'w':self.HAND_WIDTH, 'y':tbl['y'],
               'x':self.TABLE_WIDTH}
        nfo = {'h':self.DASHBOARD_HEIGHT, 'w':self.INFO_WIDTH, 'y':tbl['y'],
               'x':self.TABLE_WIDTH + self.HAND_WIDTH}

        # Set up the windows needed for Cinch.

        # Command entry:
        self.cmdline = curses.newwin(cml['h'], cml['w'], cml['y'], cml['x'])
        self.cmdpad = curses.textpad.Textbox(self.cmdline)
        self.cmdline.move(0,0)
        self.cmdline.refresh()

        # Command prompt display:
        self.cmdprompt = curses.newwin(cpt['h'], cpt['w'], cpt['y'], cpt['x'])
        self.cmdprompt.leaveok(False)
        self.cmdprompt.move(0,0)
        self.cmdprompt.addstr(self.PROMPT)
        self.cmdprompt.refresh()

        # Command output display:
        self.text_win = curses.newwin(tw['h'], tw['w'], tw['y'], tw['x'])
        self.text_win.scrollok(True)
        self.text_win.leaveok(False)

        # Table display:
        self.table = curses.newwin(tbl['h'], tbl['w'], tbl['y'], tbl['x'])
        self.table.leaveok(False)
        self.table.border()
        self.table.move(1,3)
        self.table.addstr("CINCH TABLE DISPLAY")
        self.table.refresh()

        # Hand display:
        self.hand = curses.newwin(hnd['h'], hnd['w'], hnd['y'], hnd['x'])
        self.hand.leaveok(False)
        self.hand.border()
        self.hand.move(1,4)
        self.hand.addstr("HAND")
        self.hand.refresh()

        # Info display:
        self.info = curses.newwin(nfo['h'], nfo['w'], nfo['y'], nfo['x'])
        self.info.leaveok(False)
        self.info.border()
        self.info.move(1,2)
        self.info.addstr("Game/status info will be")
        self.info.move(2,2)
        self.info.addstr("written here.")
        self.info.refresh()

    def console_input(self):
        # Run in separate input thread.
        while True:
            self.cmdline.refresh()
            self.cmd = self.cmdpad.edit()
            self._parse_command()
            self.cmdline.erase()
            self.cmdline.move(0,0)
            self.cmdline.refresh()

    def getsizes(self):
        # getmaxyx() returns the dimensions, not maxY or maxX.
        ym, xm = self.main_win.getmaxyx()
        return ym, xm

    def _parse_command(self):
        self.write(self.PROMPT + self.cmd)
        cmd = self.cmd.split()
        self.cmd = ''

    def write(self, *stuff):
        '''Display text in the console text window, scrolling the existing
        contents up as needed. This is the only method that should place text in
        this window; other methods should pass str/unicode to this one.'''
        
        # First, parse stuff into manageable chunks.
        output = []
        for thing in stuff:
            thing = str.splitlines(thing)
            for line in thing:
                output += self.textwrapper.wrap(line)

        # Then write each line in order.
        for thing in output:
            self.text_win.scroll(1)
            self.text_win.move(self.text_win.getmaxyx()[0] - 1, 0)
            self.text_win.addstr(thing)
        self.text_win.refresh()

def driver(window, flags):
    cs = CinchScreen(window)
    commandline_listener = threading.Thread(target=cs.console_input)
    commandline_listener.daemon = True
    commandline_listener.start()

    if flags['s']:
        suits = u"Suit symbol test\n♥♦♣♠.".encode("UTF-8")
        cs.write(suits)
    else:
        pass
    while True: #cs.cmd is '':
        sleep(0.1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = DESC)
    parser.add_argument("-l", "--loglevel",
                        help="set log level (default=WARNING)", type=str,
                        choices = list(LOG_SHORT.keys()), default='w')
    parser.add_argument("-a", help="testflag", action='store_true')
    parser.add_argument("-b", help="testflag1", action='store_true')
    parser.add_argument("-s", help="suittest", action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level = LOG_SHORT[args.loglevel])
    flags = {'a':args.a, 'b':args.b, 's':args.s}
    log.debug("%s", flags)
    curses.wrapper(driver, flags)
