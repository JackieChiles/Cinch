#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""Command console for Cinch server.

Requires socketIO-client package, available here:
https://github.com/invisibleroads/socketIO-client

This package will also support the AI program.

"""

# Executive summary for help page.
DESC = 'Command-line console for the Cinch card game.'

import curses
import curses.textpad

import threading
from time import sleep
from socketIO_client import SocketIO, BaseNamespace

import argparse
import logging
log = logging.getLogger(__name__)
LOG_SHORT ={'d':'DEBUG', 'i':'INFO', 'w':'WARNING', 'e':'ERROR', 'c':'CRITICAL'}

import core.gamestate as gamestate
import core.cards as cards

#TODO: Re-implement console as a small part of a virtual screen, detect window
# re-sizing and handle gracefully.

class Namespace(BaseNamespace):

    def __init__(self, *args):
        #TODO: Define RoomView or similar class that extends GameState
        # and incorporates all this garbage.

        super(Namespace, self).__init__(*args)
        self.window = None # Must connect a screen!
        self.nickname = 'NewUser' # Server auto-assigns nickname
        self.room = 0 # Server auto-assigns to the lobby.
        self.seat = None # Don't have a seat to start.
        self.gs = None # No game at first - initialized by startGame event
        self.hand = [] # self.hand will be a list of Card objects.
        self.table_view = [None, None, None, None] # Player names 0-3.

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

    #-------------------------#
    # Gamestate Update Method #
    #-------------------------#

    # Note: find better way to do this - maybe build into GameState itself?

    def gs_modify(self, msg):
        """
        Take incoming json from the server and use it to update the console's
        GameState object.

        msg: json dict from server to parse.
        """

        if msg is None:
            return
        if type(msg) is list:
            msg = msg[0] # Unpack dict enclosed in list

        if 'playC' in msg:
            if msg['actor'] == self.seat:
                self.hand.remove(cards.Card(msg['playC']))
            else:
                self.log_to_console('Seat '+str(msg['actor'])+' played '+
                                    str(cards.Card(msg['playC']))+'.')
            self.gs.cards_in_play.append(cards.Card(msg['playC']))
            if len(self.gs.cards_in_play) == 4:
                #TODO Fix this; doesn't display at correct time.
                #self.log_to_console(str(self.gs.trick_winning_card()) + 
                #                    ' won the trick.')
                self.gs.cards_in_play = []
        if 'bid' in msg:
            pass #TODO track bidding
            bid_cmts = {0:' passes.', 1:' bids 1.', 2:' bids 2.', 3:' bids 3.',
                        4:' bids 4.', 5:' cinches!'}
            self.log_to_console('Seat '+str(msg['actor'])+bid_cmts[msg['bid']])
        if 'dlr' in msg:
            self.gs.dealer = msg['dlr']
        if 'actvP' in msg:
            self.gs.active_player = msg['actvP']
        if 'addC' in msg:
            for card_code in msg['addC']:
                # Add a Card object corresponding to the code sent.
                self.hand.append(cards.Card(card_code))
        if 'mode' in msg:
            self.gs.game_mode = msg['mode']

        if self.gs.active_player == self.seat:
            if self.gs.game_mode == 2:
                action_str = 'bid.'
            else:
                action_str = 'play.'
            self.log_to_console('Your turn to ' + action_str)
            hand_str = 'Your hand: '+', '.join([str(card) for card in self.hand])
            self.log_to_console(hand_str)

    #----------------#
    # Event Handlers #
    #----------------#

    def on_ackCreate(self, room_num):
        self.log_to_console('Room '+str(room_num)+' created.')
        self.emit('join', room_num)

    def on_ackJoin(self, args):
        # Clear any game/room data when moving from room to room.
        self.gs = None # Erase current game data - no re-joins allowed yet.
        self.hand = []
        self.seat = None

        if args[0] == 0:
            self.log_to_console('You are in the lobby.')
            self.room = args[0]
        else:
            self.room = args[0]
            self.log_to_console('You are in room '+str(args[0])+'.')
            self.log_to_console('Seats available: '+str(args[1]))

    def on_ackSeat(self, seat_num):
        self.log_to_console('You have been placed in seat '+str(seat_num))
        self.seat = seat_num
        self.table_view[seat_num] = 'You'

    def on_ackNickname(self, nickname):
        resp_line = 'New nickname: '+nickname
        self.log_to_console(resp_line)
        self.nickname = nickname

    def on_bid(self, msg):
        # self.log_to_console(str(msg)) #DEBUG See on_play
        self.gs_modify(msg)

    def on_chat(self, chat_packet):
        if chat_packet[0] == self.nickname:
            pass # Don't echo self-chat messages.
        else:
            self.log_to_console(str(chat_packet[0]) + ': ' + str(chat_packet[1]))

    def on_connect(self):
        self.log_to_console('[Connected]')

    def on_disconnect(self, *args):
        self.gs = None # Erase current game data - no re-joins allowed yet.
        self.hand = []
        self.seat = None
        self.log_to_console('[Disconnected]')
        for x in args:
            self.log_to_console(str(x))

    def on_enter(self, nickname):
        self.log_to_console(nickname+' has entered the room.')

    def on_err(self, *args):
        resp_line = ''
        for err_text in args:
            resp_line += err_text
        self.log_to_console(resp_line)

    def on_exit(self, exiter):
        self.gs = None # Erase current game data - no re-joins allowed yet.
        self.hand = []
        self.seat = None
        # This kills the game memory locally if any client drops.

        self.log_to_console(str(exiter) + ' has left the room.')

    def on_play(self, msg):
        # self.log_to_console(str(msg)) #DEBUG #TODO make way to toggle in-game
        self.gs_modify(msg)
        
    def on_roomFull(self, *args):
        self.log_to_console('Room is full.')

    def on_rooms(self, room_list): #TODO Change to silent update & add command
        resp_line = "Rooms: "+', '.join(room_list)
        self.log_to_console(resp_line)
    
    def on_startData(self, msg):
        self.gs = gamestate.GameState(0) #TODO No local game_id needed for now
        self.gs_modify(msg)
        hand_str = 'Your hand: '+', '.join([str(card) for card in self.hand])
        self.log_to_console(hand_str)

    def on_userInSeat(self, json):
        if json['name'] == self.nickname:
            pass # Would duplicate message from on_ackSeat
        else:
            self.log_to_console(json['name'] + ' is now sitting in seat ' +
                                str(json['actor']) + '.')
            self.table_view[json['actor']] = json['name']

    def on_users(self, users):
        self.log_to_console('In the room: '+', '.join([str(x) for x in users]))

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
        socket.wait()

def console(scr, host='localhost', port=8088):
    """main console function. called by the curses wrapper.

    scr: curses window to write to
    host: address of the server
    port: port the server can be found on
    
    Default host:port is localhost:8088.
    """

    # Enable scrolling of command window
    scr.scrollok(True)

    # Define command prompt
    PROMPT_STR = "cinch>"

    # Establish connection
    socket = SocketIO(host, port)
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

        # test
        if cmd.startswith('test'):
            ns.emit('test', 'console', callback=ns.null_response)

        # nick
        elif cmd.startswith('nick'):
            if len(cmd) > 5:
                ns.emit('nickname', cmd[5:].strip())
            else:
                ns.log_to_console(ns.nickname)
                
        # chat
        elif cmd.startswith('chat'):
            if len(cmd) > 5:
                ns.emit('chat', cmd[5:].strip())
            else:
                ns.log_to_console('Chat message blank - no command sent.')

        # room
        elif cmd.startswith('room'):
            ns.emit('createRoom', '') # Add parameters later (see server.py)
        
        # lobby
        elif cmd.startswith('lobby'):
            ns.emit('exit', '')

        # join
        elif cmd.startswith('join'):
            try:
                room_num = int(cmd[5:])
                if ns.room <> 0:
                    ns.log_to_console('join: must be in lobby to join a room')
                else:
                    ns.emit('join', room_num)
            except ValueError:
                if len(cmd) > 5:
                    ns.log_to_console('join: can\'t make head or tails of room: '
                                      + str(cmd[5:]))
                else:
                    ns.log_to_console('join: must specify room number')

        # seat
        elif cmd.startswith('seat'):
            if len(cmd) < 5:
                self.log_to_console('seat: currently in room ' + self.room +
                                    ', seat ' + self.seat + '.')
            try:
                seat_num = int(cmd[5:])
                if seat_num > 3 or seat_num < 0:
                    raise ValueError
                ns.emit('seat', seat_num)
            except ValueError:
                ns.log_to_console('seat: bad seat number')

        # ai
        elif cmd.startswith('ai'):
            ns.log_to_console('--future--') #TODO

        # bid
        elif cmd.startswith('bid'):
            try:
                if cmd[4:].strip().lower() in ['cinch', 'c']:
                    ns.emit('bid', 5)
                elif cmd[4:].strip().lower() in ['pass', 'p']:
                    ns.emit('bid', 0)
                else:
                    bid = int(cmd[4:])
                    if bid > 5 or bid < 0:
                        raise OverflowError
                    ns.emit('bid', bid)
            except ValueError:
                ns.log_to_console('bid: couldn\'t understand bid')
            except OverflowError:
                ns.log_to_console('bid: bid out of range [0-5, cinch, pass]')

        # play
        elif cmd.startswith('play'):
            try:
                # Strict NS-style shorthand for now; #TODO develop better UI later
                play = cmd[5:].strip().upper()
                ivRANKS_SHORT = {v: k for k, v in cards.RANKS_SHORT.items()}
                ivSUITS_SHORT = {v: k for k, v in cards.SUITS_SHORT.items()}
                p_card = cards.Card(ivRANKS_SHORT[play[0]], ivSUITS_SHORT[play[1]])
                ns.emit('play', p_card.encode())
            except Exception as e:
                ns.log_to_console(str(e))

        #hand 
        elif cmd.startswith('hand'):
            hand_str = 'Your hand: '+', '.join([str(card) for card in self.hand])
            self.log_to_console(hand_str)

    # Disconnect
    socket.disconnect()
    
#----------------#
# Curses Wrapper #
#----------------#

def main(host, port):
    curses.wrapper(console, host, port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = DESC)
    parser.add_argument("-l", "--loglevel",
                        help="set log level (default=WARNING)", type=str,
                        choices = list(LOG_SHORT.keys()), default='w')
    parser.add_argument("--host", help="hostname (default=localhost)", type=str,
                        default='localhost')
    parser.add_argument("-p", "--port", help="port no. (default=8088)",
                        type=int, default=8088)
    args = parser.parse_args()
    logging.basicConfig(level = LOG_SHORT[args.loglevel])

    main(args.host, args.port)

