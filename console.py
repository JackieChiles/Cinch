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
             ['aig', r'^$', '(null): quickstart ai game for testing'],
             ['lobby', r'^$', '(null): leave current room and join lobby'],
             ['join', r'^[0-9]+$', 'N: join room N'],
             ['help', r'^$|^-v$', '[-v]: list registered commands [-v w/regex]'],
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


import core.game as game
import core.gamestate as gamestate
import core.cards as cards


class RoomView(gamestate.GameState):
    '''This class extends GameState for use by the console client. A RoomView
    should be created/deleted upon entry/exit from a room.'''

    def __init__(self, *args):
        super(RoomView, self).__init__(0)
        self.room = None
        self.seat = None
        self.hand = [] # self.hand will be a list of Card objects.
        self._table_view = [None, None, None, None] # Player names 0-3.

    def __del__(self):
        # Need to reset all room-specific items on the display.
        cs.update_dash('hand', []) # Clear Hand panel.
        for x in range(game.NUM_PLAYERS):
            cs.update_dash('seat', x, '')
            cs.update_dash('bid', x, None)
            cs.update_dash('card', x, '')
        cs.update_dash('dealer', None)

    #-------------------------#
    # Gamestate Update Method #
    #-------------------------#

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
        if 'mode' in msg: # Must be processed before 'bid' due to dashboard.
            self.game_mode = msg['mode']
            if self.game_mode == game.GAME_MODE.BID:
                # Clear all bids from play area before processing new.
                for x in range(game.NUM_PLAYERS):
                    cs.update_dash('bid', x, None)
        if 'bid' in msg:
            apparent_seat = (msg['actor'] - self.seat) % game.NUM_PLAYERS
            cs.update_dash('bid', apparent_seat, msg['bid'])
        if 'dlr' in msg:
            self.dealer = msg['dlr']
        if 'actvP' in msg:
            self.active_player = msg['actvP']
        if 'addC' in msg:
            for card_code in msg['addC']:
                # Add a Card object corresponding to the code sent.
                self.hand.append(cards.Card(card_code))
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

    def update_table(self, username, seat_num, action='add'):
        '''Call this method when adding or removing users from seats. It will
        automatically update the dashboard if the user is in a seat.'''
        if not (action is 'add' or action is 'remove'):
            log.error('rv.update_table called with invalid action %s', action)
            return
        if action is 'add':
            self._table_view[seat_num] = username
        if action is 'remove':
            self._table_view[seat_num] = None
        if self.seat is not None:
            # User is in a seat so users can be drawn at their seats.
            for actual_seat, player in enumerate(self._table_view):
                if player is None:
                    nick = ''
                else:
                    nick = player
                apparent_seat = (actual_seat - self.seat) % game.NUM_PLAYERS
                cs.update_dash('seat', apparent_seat, nick) 

class Namespace(BaseNamespace):

    def __init__(self, *args):
        super(Namespace, self).__init__(*args)
        self.ai_list = []
        self.nickname = 'NewUser' # Assigned but not transmitted by server.

    #----------------#
    # Event Handlers #
    #----------------#

    def ackCreate(self, room_num):
        log.info('Room '+str(room_num)+' created.')
        self.emit('join', room_num, self.ackJoin)

    def ackJoin(self, *args):
        # Clear any game/room data when moving from room to room.
        self.rv = RoomView(0) # Set up a RoomView to hold game info.
        if args[0]['seatChart'] == 'lobby':
            log.info('You are in the lobby.')
            del self.rv
        else:
            self.rv.room = args[0]['roomNum']
            log.info('You are in room ' +str(self.rv.room)+'.') #TODO-dashboard
            for player in args[0]['seatChart']:
                # SeatCharts are lists of (username, seat) pairs.
                if int(player[1]) == -1: # Username not in a seat...
                    pass #TODO-dashboard put in status panel?
                else:
                    self.rv.update_table(player[0], int(player[1]))

    def on_ackSeat(self, seat_num):
        if hasattr(self, 'rv'):
            log.info('You have been placed in seat '+str(seat_num))
            self.rv.seat = seat_num
            self.rv.update_table(self.nickname, seat_num)
        else:
            raise RuntimeError('Got ackSeat while not in a room??')

    def ackNickname(self, nickname):
        if nickname is None:
            return
        resp_line = 'New nickname: '+nickname
        log.info(resp_line)
        self.nickname = nickname

    def on_aiInfo(self, bot_list):
        self.ai_list = bot_list # Refreshes ai_info but doesn't display.
        log.info('Updated AI agent list.')

    def on_bid(self, msg):
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
        self.rv.modify(msg)
        cs.update_dash('hand', [str(card) for card in self.rv.hand])
        
    def on_roomFull(self, *args):
        log.info('Room is full.')

    def on_rooms(self, room_list): #TODO Change to silent update & add command
        # room_list is a dict with items name and num
        resp_line = "Rooms: "+', '.join([x['name'] for x in room_list])
        log.info(resp_line)
    
    def on_startData(self, msg):
        self.rv.modify(msg)
        cs.update_dash('hand', [str(card) for card in self.rv.hand])

    def on_seatChart(self, chart):
        # Final seat chart is sent as list of len-2 lists [u'nick', seat_num]
        for entry in chart:
            self.rv.update_table(entry[0], entry[1])

    def on_userInSeat(self, json):
        if json['name'] == self.nickname:
            pass # Would duplicate message from on_ackSeat
        else:
            log.info(json['name'] + ' is now sitting in seat ' +
                                str(json['actor']) + '.')
            self.rv.update_table(json['name'], json['actor'])

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
    global cs 
    with cinchscreen.CinchScreen(window, log) as cs:

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
            cs.register_command(*c)
    
        # Listen to the console.
        try:
            while True:
                while cs.queue.empty():
                    sleep(0.1)
                cmd = cs.queue.get(timeout=0.2)
    
                # Process the command.
    
                # test
                if 'test' in cmd:
                    ns.emit('test', 'console')
                elif 'help' in cmd:
                    for command in COMMANDS:
                        output = command[0] + ': ' + command[2]
                        if 'v' in cmd['help']:
                            output += r' (regex: /' + command[1] + r'/)'
                        cs.write(output)
                elif 'nick' in cmd:
                    if cmd['nick'] == '':
                        cs.write(ns.nickname) #TODO RoomView
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
                elif 'aig' in cmd:
                    # Quickstart a 3-ai game.
                    ns.emit('createRoom', {1:1,2:1,3:1}, ns.ackCreate)
                elif 'lobby' in cmd:
                    ns.emit('exit', '', ns.ackJoin)
                    # Need to listen for confirmation we're back in lobby...
                elif 'join' in cmd:
                    try:
                        room_num = int(cmd['join'])
                        if not hasattr(ns, 'rv'): # No RoomView = in lobby
                            cs.write('join: must be in lobby to join a room')
                        else:
                            ns.emit('join', room_num, ns.ackJoin)
                    except ValueError:
                        log.exception('join: arg from queue: %s', cmd['join'])
                        log.error('join: A problem occurred.')
                elif 'seat' in cmd:
                    if cmd['seat'] == '':
                        if hasattr(ns, 'rv'):
                            log.info('seat: currently in room %s, seat %s',
                                     str(ns.rv.room), str(ns.rv.seat))
                        else:
                            log.info('seat: currently in lobby')
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
                        cs.write("Available AI agents:")
                        for ai in ns.ai_list:
                            cs.write(str(ai['id']) + ': ' + ai['name'] +
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
                    # Write current hand contents to console as well as dash.
                    if not hasattr(ns, 'rv'):
                        log.info("No hand - not in a game.")
                    else:
                        hand_str = ('Your hand: ' +
                                    ', '.join([str(card) for card in ns.rv.hand]))
                        cs.write(hand_str)
                        cs.update_dash('hand', [str(card) for card in ns.rv.hand])
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

    log.setLevel(LOG_SHORT[args.loglevel])
    curses.wrapper(console, args.host, args.port)
