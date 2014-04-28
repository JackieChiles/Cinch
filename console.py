#!/usr/bin/python2
# -*- coding: utf-8 -*-
"""Command console for Cinch server.

Requires socketIO-client package, available here:
https://github.com/invisibleroads/socketIO-client

This package will also support the AI program.

"""

# Executive summary for help page.
DESC = 'Command-line console for the Cinch card game.'

import core.curses_interface as cinchscreen
import curses
# List of commands to register with curses interface.
COMMANDS = [ ['test', r'^$', '(null): test connection to server'],
             ['nick', r'^.*', '[<str>]: display nick or change to <str>'],
             ['chat', r'^.*', '<str>: send message <str> to current room'],
             ['room', r'^([0-3]:\d+\s+){0,3}([0-3]:\d+)?$',
              '[<seat>:<ai_id> x0-4]: spawn new room [with opt. ai seating]'],
             ['lobby', r'^$', '(null): leave current room and join lobby'],
             ['join', r'^[0-9]+$', 'N: join room N'],
             ['help', r'^[v]?$', '[v]: list registered commands [-v w/regex]'],
             ['seat', r'^[0-3]?$', '[N]: show seat or sit in seat N (0-3)'],
             ['ai', r'^(list|refresh)$',
              'list: show AIs | refresh: get list from server'],
             ['bid', r'^[0-5]$|^[Cc]{1}(inch|INCH)?$|^[Pp]{1}(ass|ASS)?$',
              '0-5, c[inch], p[ass]: send bid to server'],
             ['play', r'^[2-9TtJjQqKkAa][CcDdHhSs]$', 'NS: play card'],
             ['hand', r'^$', '(null): display your current cards in hand'],
             ['exit', r'^.*', 'unconditional quit']
           ]


import threading
from time import sleep
from socketIO_client import SocketIO, BaseNamespace

import sys
import argparse
import logging
log = logging.getLogger(__name__)
LOG_SHORT ={'d':'DEBUG', 'i':'INFO', 'w':'WARNING', 'e':'ERROR', 'c':'CRITICAL'}

import core.gamestate as gamestate
import core.cards as cards


class RoomView(gamestate.GameState):
    def __init__(self, *args):
        super(RoomView, self).__init__(0)
        self.room = None
        self.seat = None
        self.hand = [] # self.hand will be a list of Card objects.
        self.table_view = [None, None, None, None] # Player names 0-3.

    #-------------------------#
    # Gamestate Update Method #
    #-------------------------#

    # Note: find better way to do this - maybe build into GameState itself?

    def modify(self, msg):
        """
        Take incoming json from the server and use it to update the console's
        GameState object.

        msg: json dict from server to parse.
        """

        if msg is None:
            return
        elif type(msg) is dict:
            pass # This is the expected case.
        elif type(msg) is list:
            msg = msg[0] # Unpack dict enclosed in list
        else:
            raise TypeError("Couldn't unpack dictionary from JSON object: %s", msg)

        if 'playC' in msg:
            if msg['actor'] == self.seat:
                self.hand.remove(cards.Card(msg['playC']))
            else:
                log.info('Seat '+str(msg['actor'])+' played '+
                                    str(cards.Card(msg['playC']))+'.')
            self.cards_in_play.append(cards.Card(msg['playC']))
            if 'remP' in msg:
                log.info('Seat ' + str(msg['remP']) + ' won the trick.')
                self.cards_in_play = []
        if 'bid' in msg:
            pass #TODO track bidding
            bid_cmts = {0:' passes.', 1:' bids 1.', 2:' bids 2.', 3:' bids 3.',
                        4:' bids 4.', 5:' cinches!'}
            log.info('Seat '+str(msg['actor'])+bid_cmts[msg['bid']])
        if 'dlr' in msg:
            self.dealer = msg['dlr']
        if 'actvP' in msg:
            self.active_player = msg['actvP']
        if 'addC' in msg:
            for card_code in msg['addC']:
                # Add a Card object corresponding to the code sent.
                self.hand.append(cards.Card(card_code))
        if 'mode' in msg:
            self.game_mode = msg['mode']
        if 'sco' in msg:
            self.scores = msg['sco']
            log.info('Scores: You ' + str(self.scores[self.seat % 2]) +
                     ', them ' + str(self.scores[(self.seat + 1) % 2]))

        if self.active_player == self.seat:
            if self.game_mode == 2:
                action_str = 'bid.'
            else:
                action_str = 'play.'
            log.info('Your turn to ' + action_str)
            hand_str = 'Your hand: '+', '.join([str(card) for card in self.hand])
            log.info(hand_str)


class CursesLogger(object):
    def __init__(self, curses_stream):
        self.cs = curses_stream

    def __enter__(self):
        #TODO: There is probably a better way of redirecting logging to the
        #curses screen.
        self._old_stderr = sys.stderr
        sys.stderr = self.cs # Capture tracebacks and display nicely

        self.log = logging.getLogger(__name__)
        self.log.propagate = False
        if (self.log.level > logging.INFO) or (self.log.level == 0):
            self._old_log_level = self.log.level
            self.log.setLevel(logging.INFO)
        self.log.addHandler(logging.StreamHandler(self.cs))

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.log.handlers = []
        try:
            self.log.setLevel(self._old_log_level)
        except AttributeError:
            pass
        sys.stderr = self._old_stderr
        self.log.propagate = True
        self.log.debug("Logged after executing self.__exit__()")


class Namespace(BaseNamespace):

    def __init__(self, *args):
        super(Namespace, self).__init__(*args)
        self.ai_list = []
        self.rv = None
        self.nickname = 'NewUser' # Assigned but not transmitted by server.

    #----------------#
    # Event Handlers #
    #----------------#

    def ackCreate(self, room_num):
        log.info('Room '+str(room_num)+' created.')
        self.emit('join', room_num, self.ackJoin)

    def ackJoin(self, args):
        # Clear any game/room data when moving from room to room.
        self.rv = RoomView(0) # Set up a RoomView to hold game info.

        log.info(args)###
        if args['roomNum'] == 0:
            log.info('You are in the lobby.')
            self.rv = None
        else:
            self.rv.room = args['roomNum']
            log.info('You are in room ' +str(self.rv.room)+'.')
            log.info('Seats available: ' + str(args['seatChart']))

    def on_ackSeat(self, seat_num):
        log.info('You have been placed in seat '+str(seat_num))
        self.rv.seat = seat_num
        self.rv.table_view[seat_num] = 'You'

    def ackNickname(self, nickname):
        resp_line = 'New nickname: '+nickname
        log.info(resp_line)
        self.nickname = nickname

    def on_aiInfo(self, bot_list):
        self.ai_list = bot_list # Refreshes ai_info but doesn't display.
        log.info('Updated AI agent list.')

    def on_bid(self, msg):
        # log.info(str(msg)) #DEBUG See on_play
        self.rv.modify(msg)

    def on_chat(self, chat_packet):
        if chat_packet[0] == self.nickname:
            log.info('You: ' + str(chat_packet[1])) #TODO enable custom echo
        else:
            log.info(str(chat_packet[0]) + ': ' + str(chat_packet[1]))

    def on_connect(self):
        log.info('[Connected]')

    def on_disconnect(self, *args):
        self.rv = None # Erase current game data - no re-joins allowed yet.
        log.info('[Disconnected]')
        for x in args:
            log.info(str(x))

    def on_enter(self, nickname):
        log.info(nickname+' has entered the room.')

    def on_err(self, *args):
        resp_line = ''
        for err_text in args:
            resp_line += err_text
        log.info(resp_line)

    def on_exit(self, exiter):
        log.info(str(exiter) + ' has left the room.')

    def on_play(self, msg):
        # log.info(str(msg)) #DEBUG #TODO make way to toggle in-game
        self.rv.modify(msg)
        
    def on_roomFull(self, *args):
        log.info('Room is full.')

    def on_rooms(self, room_list): #TODO Change to silent update & add command
        # room_list is a dict with items name and num
        resp_line = "Rooms: "+', '.join([x['name'] for x in room_list])
        log.info(resp_line)
    
    def on_startData(self, msg):
        self.rv.modify(msg)
        hand_str = 'Your hand: '+', '.join([str(card) for card in self.rv.hand])
        log.info(hand_str)

    def on_userInSeat(self, json):
        if json['name'] == self.nickname:
            pass # Would duplicate message from on_ackSeat
        else:
            log.info(json['name'] + ' is now sitting in seat ' +
                                str(json['actor']) + '.')
            self.rv.table_view[json['actor']] = json['name']

    def on_users(self, users):
        log.info('In the room: '+', '.join([str(x) for x in users]))

    #--------------------------------#
    # Callback Handler - for testing #
    #--------------------------------#

    def cmd_response(*args):
        resp_line = ''
        for x in args:
            resp_line += x
        log.info(resp_line)


def listen_to_server(socket):
    '''
    Handles incoming data from server.
    Should be run in a separate thread to avoid blocking main console thread.
    '''

    while True:
        try:
            socket.wait()
        except Exception:
            log.exception("Exception caught while handling event.")

def console(window, host='localhost', port=8088):
    """Main console function. Inits all other modules/classes as needed.
    
    window: curses wrapper window
    host: address of the server
    port: port the server can be found on
    
    Default host:port is localhost:8088.
    """
    # Initialize curses interface
    cs = cinchscreen.CinchScreen(window)

    with CursesLogger(cs) as cl:

        # Establish server connection
        socket = SocketIO(host, port)
        listener = threading.Thread(target=listen_to_server, args=(socket,))
        listener.daemon = True
        listener.start()
        ns = socket.define(Namespace, '/cinch')
    
    
        # Test & initialize connection
        sleep(0.5)
        ns.emit('test', 'console')
    
    
        # Register commands.
        # commands - list of 3-string lists (name, regex, usage).
        for c in COMMANDS:
            cl.cs.register_command(*c)
    
        # Listen to the console.
        try:
            while True:
                while cl.cs.queue.empty():
                    sleep(0.1)
                cmd = cl.cs.queue.get(timeout=0.2)
    
                # Process the command.
    
                # test
                if 'test' in cmd:
                    ns.emit('test', 'console')
                elif 'help' in cmd:
                    for command in COMMANDS:
                        output = command[0] + ': ' + command[2]
                        if 'v' in cmd['help']:
                            output += r' (regex: /' + command[1] + r'/)'
                        cl.cs.write(output)
                elif 'nick' in cmd:
                    if cmd['nick'] == '':
                        cl.cs.write(ns.nickname) #TODO RoomView
                    else:
                        ns.emit('nickname', cmd['nick'], ns.ackNickname)
                        #TODO status window update nick
                elif 'chat' in cmd:
                    ns.emit('chat', cmd['chat'])
                elif 'room' in cmd:
                    #if cmd['room'] == '':
                    #    ns.emit('createRoom', '')
                    #else:
                    try:
                        ai_requests = cmd['room'].split()
                        ai_req_output = {}
                        for request in ai_requests:
                            x = request.split(':')
                            ai_req_output[int(x[0])] = int(x[1])
                        ns.emit('createRoom', ai_req_output, ns.ackCreate)
                    except ValueError:
                        log.exception('room: arg from queue: %s', cmd['room'])
                        log.error('room: A problem occurred.')
                elif 'lobby' in cmd:
                    ns.emit('exit', '')
                elif 'join' in cmd:
                    try:
                        room_num = int(cmd['join'])
                        if ns.rv is not None: # Not in a room; must be in the lobby
                            cl.cs.write('join: must be in lobby to join a room')
                        else:
                            ns.emit('join', room_num, ns.ackJoin)
                    except ValueError:
                        log.exception('join: arg from queue: %s', cmd['join'])
                        log.error('join: A problem occurred.')
                elif 'seat' in cmd:
                    if cmd['seat'] == '':
                        cl.cs.write('seat: currently in room ' +
                                    str(ns.rv.room) + ', seat ' +
                                    str(ns.rv.seat) + '.')
                    else:
                        try:
                            seat_num = int(cmd['seat'])
                            ns.emit('seat', seat_num)
                        except ValueError:
                            log.exception('seat: arg from queue: %s',
                                          cmd['seat'])
                            log.error('seat: A problem occurred.')
                elif 'ai' in cmd:
                    if cmd['ai'] == 'refresh':
                        ns.emit('aiList', '')
                    elif cmd['ai'] == 'list':
                        cl.cs.write("Available AI agents:")
                        for ai in ns.ai_list:
                            cl.cs.write(str(ai['id']) + ': ' + ai['name'] +
                                        ' - ' + ai['desc'])
                    else:
                        try:
                            raise ValueError
                        except ValueError:
                            log.exception("ai: couldn't handle arg %s", cmd['ai'])
                elif 'bid' in cmd:
                    if cmd['bid'].lower() in ['cinch', 'c']:
                        ns.emit('bid', 5)
                    elif cmd['bid'].lower() in ['pass', 'p']:
                        ns.emit('bid', 0)
                    else:
                        try:
                            ns.emit('bid', int(cmd['bid']))
                        except ValueError:
                            log.exception('bid: arg from queue: %s',
                                          cmd['bid'])
                            log.error('bid: A problem occurred.')
                elif 'play' in cmd:
                    try:
                        # Strict NS-style shorthand for now
                        #TODO develop better UI later
                        ivRANKS_SHORT = {v: k for k, v in cards.RANKS_SHORT.items()}
                        ivSUITS_SHORT = {'C':0, 'D':1, 'H':2, 'S':3}
                        p_card = cards.Card(ivRANKS_SHORT[cmd['play'].upper()[0]],
                                            ivSUITS_SHORT[cmd['play'].upper()[1]])
                        ns.emit('play', p_card.encode())
                    except Exception:
                        log.exception('play: generic problem')
                elif 'hand' in cmd:
                    hand_str = ('Your hand: ' +
                                ', '.join([str(card) for card in ns.rv.hand]))
                    cl.cs.write(hand_str)
                elif 'exit' in cmd:
                    raise SystemExit
    
        except KeyboardInterrupt:
            log.warning("C-c detected; exiting...")
        except SystemExit:
            log.warning("Exiting...")
    
        # Disconnect
        socket.disconnect()
    
#---------------------------#
# Argparse & Curses Wrapper #
#---------------------------#

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

    curses.wrapper(console, args.host, args.port)
