#!/usr/bin/python2
# coding=UTF-8
"""Curses interface for Cinch console."""

# currently being used for debugging.

DESC = "Cinch console curses interface class, along with driver for same."

import curses
import curses.textpad
import sys

import locale
locale.setlocale(locale.LC_ALL,"")

import threading
from time import sleep

from textwrap import TextWrapper
from Queue import Queue
import re

import argparse
import logging
import logging.config
log = logging.getLogger(__name__)
LOG_SHORT ={'d':'DEBUG', 'i':'INFO', 'w':'WARNING', 'e':'ERROR', 'c':'CRITICAL'}


class CinchScreen():
    def __init__(self, main_win, global_log):
        # Pass logging.getLogger(__name__) to enforce info-level logging.
        # Also set other loggers to original log level.
        self.log = global_log

        self.main_win = main_win        
        self.ym, self.xm = self.getsizes()
        self.PROMPT = "cinch> "
        self.textwrapper = TextWrapper(width = self.xm) # used in write()
        self.cmd = '' # User input command; starts blank.
        self.queue = Queue() # Where parsed commands go.

        # These dicts hold the names of valid commands as keys. The values of
        # _valid_commands are the regexes corresponding to allowable arguments.
        # The values of _command_usage are the strings to print in response to
        # invalid input or to a 'help'-class command. They should be accessed
        # through register_command() and deregister_command().

        self._valid_commands = {}
        self._command_usage = {}
        self._write_lock = threading.Lock() # Make write() thread-safe.

        # Define sub-window dimensions here.

        # First define the functional layout.
        self.DASHBOARD_HEIGHT = 12
        self.COMMAND_HEIGHT = 1
        self.TABLE_WIDTH = 26
        self.HAND_WIDTH = 6
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
        self.table.move(1,8)
        self.table.addstr("PLAY  AREA")

        # Draw table graphic:
        self.table.move(4,9)
        self.table.addstr("┌──────┐")
        for x in range(5,8):
            self.table.move(x,9)
            self.table.addstr("│      │")
        self.table.move(8,9)
        self.table.addstr("└──────┘")

        # Add constants for writing table data:
        self.TBL_NAMES  = [( 9, 9), (5, 1), (2, 9), (5,17)]
        self.TBL_NAME_LEN = 8
        self.TBL_CARDS  = [( 7,12), (6,10), (5,12), (6,14)]
        self.TBL_BIDS   = [(10, 9), (6, 1), (3, 9), (6,17)]
        self.TBL_DEALER = [( 7,10), (5,10), (5,15), (7,15)]
        self.table.refresh()

        # Hand display:
        self.hand = curses.newwin(hnd['h'], hnd['w'], hnd['y'], hnd['x'])
        self.hand.leaveok(False)
        self.hand.border()
        self.hand.move(1,1)
        self.hand.addstr("HAND")
        self.hand.refresh()

        # Info display:
        self.LAST_TRICK_DISP = [(3,2), (3,5), (3,8), (3,11)]
        self.LAST_TAKER_DISP = (2,2)
        self.LAST_TAKER_LEN = 14
        
        self.TRUMP_DISP = (self.DASHBOARD_HEIGHT - 2, 9)

        self.US_SCORE_DISP = (3, self.INFO_WIDTH - 5)
        self.THEM_SCORE_DISP = (6, self.INFO_WIDTH - 5)

        self.info = curses.newwin(nfo['h'], nfo['w'], nfo['y'], nfo['x'])
        self.info.leaveok(False)
        self.info.border()
        self.info.move(1,2)
        self.info.addstr('--Last trick--')
        self.info.move(self.DASHBOARD_HEIGHT - 2, 2)
        self.info.addstr('Trump:')

        self.SCORES_TEMPLATE = ['   Scores  ',
                                '      ┌───┐',
                                ' Us:  │   │',
                                '      └───┘',
                                '      ┌───┐',
                                ' Them:│   │',
                                '      └───┘']
        for x in range(1,8):
            self.info.move(x, self.INFO_WIDTH - 12)
            self.info.addstr(self.SCORES_TEMPLATE[x-1])
        self.info.refresh()

        commandline_listener = threading.Thread(target=self._console_input)
        commandline_listener.daemon = True
        commandline_listener.start()
        
    def __enter__(self):
        # Capture stderr.
        self._old_stderr = sys.stderr
        sys.stderr = self # Capture tracebacks and display nicely

        # Capture all loggers.
        for x in logging.Logger.manager.loggerDict:
            x_log = logging.getLogger(x)
            x_log.addHandler(logging.StreamHandler(self))
            x_log.setLevel(self.log.level)

        # INFO level logging used for most command responses; enable them.
        if (self.log.level > logging.INFO) or (self.log.level == 0):
            self._old_log_level = self.log.level
            self.log.setLevel(logging.INFO)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Reset previous logging (undo INFO level set)
        try:
            self.log.setLevel(self._old_log_level)
        except AttributeError:
            pass

        # Remove cinchscreen handlers
        for x in logging.Logger.manager.loggerDict:
            logging.getLogger(x).handlers = []

        # Reset stderr
        sys.stderr = self._old_stderr

        log.debug("Logged after executing self.__exit__()")

    def _console_input(self):
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
        '''
        Called by console_input. Takes input lines from cmdpad, echoes to the
        screen, parses, and adds well-formed commands to the queue. Rejects
        bad syntax, but bad input parameters will be checked by the console.
        '''
        # FUTURE: Write parallel method to handle getch() mode.

        # First, echo the command to the output window.
        # Later, consider adding an option to set echo to all, 
        # all but chats or none.

        self.write(self.PROMPT + self.cmd)

        if self.cmd == '':
            return

        cmd_name = self.cmd.split()[0]

        # Command syntax: "name <args>", where args matches the cmd regex.
        if cmd_name in self._valid_commands:
            # Valid command name; check arg syntax
            cmd_args = self.cmd[len(cmd_name):].strip() # Rem. name & whitespace
            if self._valid_commands[cmd_name].match(cmd_args):
                # OK syntax; add to queue
                self.queue.put({cmd_name:cmd_args})
            else:
                # Syntax not OK; print usage
                self.write(cmd_name + ": " + self._command_usage[cmd_name]
                           + " (" + cmd_args + " received)")
        else:
            # Not a valid command name
            self.write(cmd_name + ": not a valid command")
        
        self.cmd = '' # Unblock the listener.

    def register_command(self, name, regex=r'^$', usage='usage not supplied'):
        '''
        The main console calls this on init to add recognized commands.
        name: Name of the command. Does not include any cmdline-specific control
              characters (such as '/'); this will be CinchScreen's choice.
        regex: Raw string containing a regex representing valid arg strings.
               User input will be parsed and rejected if it doesn't match.
        usage: The console will echo the command name and this string to the
               screen if invalid input is detected.
        '''
        
        self._valid_commands[name] = re.compile(regex)
        self._command_usage[name] = usage

    def unregister_command(self, name):
        '''
        Remove a command from the list of valid commands.
        name: name of the command to remove.
        '''
        try:
            del self._valid_commands[name]
            del self._command_usage[name]
        except KeyError:
            self.write("KeyError deleting command " + name + ": not found")

    def update_dash(self, msg_type, *args):
        '''Display information in the dashboard. Most game events should affect
        the dashboard in some way.
        
        msg_type(str): Type of update to process. Allowed values will affect the
                       required *args.

        Currently allowed msg_type values:
        
        msg_type  |   args
        ----------|-------
        'hand'    |   A len-[0..9] list of NS-style strings.
        'seat'    |   An apparent_seat and nickname ('' to clear).
        'bid'     |   An apparent_seat and bid (int or None).
        'card'    |   An apparent_seat and card (NS-style or None).
        'last'    |   A line num (0-3) and card (NS-style or None).
        'taker'   |   A username, None, or ''.
        'scores'  |   A 2-tuple with Us/Them scores or None.
        'trump'   |   A suit symbol or None.
        'dealer'  |   <not implemented yet>
        '''

        try:
            #----< Hand Window Updates >----#
            if msg_type is 'hand':
                h_upd = args[0]

                # Do some validation on input
                if type(h_upd) is not list:
                    log.error("update_dash(hand): hand data not list")
                    return
                if len(h_upd) > 9:
                    log.error("update_dash(hand): too many cards")
                    return

                # Pad to 9 entries to overwrite old hand
                while len(h_upd) < 9:
                    h_upd.append('  ')

                # Write cards to screen
                for k,v in dict(zip(range(2,11),h_upd)).iteritems():
                    self.hand.move(k,2)
                    self.hand.addstr(v)
                    self.hand.refresh()

            #----< Table Window Updates >----#
            elif msg_type is 'seat':
                apparent_seat = args[0]
                nickname = args[1]
                # Truncate long names
                if len(nickname) > self.TBL_NAME_LEN:
                    nickname = nickname[:(self.TBL_NAME_LEN - 1)] + '>'
                # Pad short names
                while len(nickname) < self.TBL_NAME_LEN:
                    nickname += ' '
                # Write nickname to appropriate slot
                self.table.move(*self.TBL_NAMES[apparent_seat])
                self.table.addstr(nickname)
                self.table.refresh()
            
            elif msg_type is 'bid':
                apparent_seat = args[0]
                bid = args[1]
                bid_strings = {None:'', 0:'Pass', 1:'Bid 1',
                               2:'Bid 2', 3:'Bid 3', 4:'Bid 4', 5:'Cinch!'}
                try:
                    bid_str = bid_strings[bid]
                except KeyError:
                    log.exception("Unrecognized bid %s", bid)
                    bid_str = '????'
                while len(bid_str) < self.TBL_NAME_LEN:
                    bid_str += ' '
                self.table.move(*self.TBL_BIDS[apparent_seat])
                self.table.addstr(bid_str)
                self.table.refresh()
                
            elif msg_type is 'card':
                apparent_seat = args[0]
                card = args[1]
                if card is None:
                    card = '  '
                self.table.move(*self.TBL_CARDS[apparent_seat])
                self.table.addstr(card)
                self.table.refresh()

            #----< Info Window Updates >----#
            elif msg_type is 'last':
                line = args[0]
                card = args[1]
                if card is None:
                    card = '  '
                self.info.move(*self.LAST_TRICK_DISP[line])
                self.info.addstr(card)
                self.info.refresh()
            
            elif msg_type is 'taker':
                taker = args[0]
                if (taker is None) or (taker is ''):
                    taker = ''
                else:
                    taker = taker + ' took:'
                if len(taker) > self.LAST_TAKER_LEN:
                    taker = taker[:self.LAST_TAKER_LEN - 7] + '> took:'
                while len(taker) < self.LAST_TAKER_LEN:
                    taker += ' '
                self.info.move(*self.LAST_TAKER_DISP)
                self.info.addstr(taker)
                self.info.refresh()

            elif msg_type is 'scores':
                log.debug('cs.update_dash--scores: %s', args)
                if args[0] is None:
                    us_score = '   '
                    them_score = '   '
                else:
                    us_score = args[0][0]
                    them_score = args[0][1]
                us_score = (str(us_score) + '   ')[:3]
                them_score = (str(them_score) + '   ')[:3]
                self.info.move(*self.US_SCORE_DISP)
                self.info.addstr(us_score)
                self.info.move(*self.THEM_SCORE_DISP)
                self.info.addstr(them_score)
                self.info.refresh()

            elif msg_type is 'trump':
                log.debug('cs.update_dash--trump: %s', args)
                if args[0] is None:
                    trump = ' '
                else:
                    trump = args[0]
                self.info.move(*self.TRUMP_DISP)
                self.info.addstr(trump)
                self.info.refresh()

            elif msg_type is 'dealer':
                pass #TODO

            #----< Handle invalid input >----*
            else:
                log.error("msg_type %s not valid in update_dash", msg_type)
        finally:
            self.cmdline.refresh() # Set displayed cursor back to cmdline.

    def write(self, *stuff):
        '''Display text in the console text window, scrolling the existing
        contents up as needed. This is the only method that should place text in
        this window; other methods should pass str/unicode to this one.'''
        
        with self._write_lock:
            # First, parse stuff into manageable chunks.
            output = []
            for thing in stuff:
                if type(thing) == unicode:
                    thing = unicode.splitlines(thing)
                else:
                    thing = str.splitlines(thing)
                for line in thing:
                    output += self.textwrapper.wrap(line)
            # Then write each line in order.
            for thing in output:
                self.text_win.scroll(1)
                self.text_win.move(self.text_win.getmaxyx()[0] - 1, 0)
                self.text_win.addstr(thing)
                self.text_win.refresh()
                self.cmdline.refresh() # Set displayed cursor back to cmdline.


def driver(window, flags):
    with CinchScreen(window) as cs:
        cs.write('Console interface test driver.')
        cs.write('------------------------------')
        if flags['s']:
            suits = u"Suit symbol test\n♥♦♣♠.".encode("UTF-8")
            cs.write(suits)
        if flags['a']:
            cs.register_command('test', r'^[0-9]$', "test N (single digit only)")
        if flags['b']:
            cs.unregister_command('test')
        if flags['w']:
            cs.log.critical(cs.log.level)
            cs.log.info("i: Testing curses-based logging handlers...")
            cs.log.debug("d: Shouldn't see me unless -l d flag set!")
            cs.log.error("e: Oh, what a night; Late December back in sixty three; What a very special time for me; As I remember, what a night!")
            cs.log.info("i: Cette année-là; je chantais pour la première fois; le public ne me connaissait pas; oh quelle année cette année-la ! (Jumping jacks!)")
            cs.write("cs.write call")
        while True:
            sleep(0.1)
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = DESC)
    parser.add_argument("-l", "--loglevel",
                        help="set log level (default=WARNING)", type=str,
                        choices = list(LOG_SHORT.keys()), default='w')
    parser.add_argument("-a", help="reg test cmd", action='store_true')
    parser.add_argument("-w", help="test logging with write()", action='store_true')
    parser.add_argument("-b", help="del test cmd", action='store_true')
    parser.add_argument("-s", help="suittest", action='store_true')
    args = parser.parse_args()
    log.setLevel(LOG_SHORT[args.loglevel])
    flags = {'a':args.a, 'b':args.b, 'w':args.w, 's':args.s}
    log.debug("%s", flags)
    curses.wrapper(driver, flags)
