#!/usr/bin/python3
"""Base functionality for Cinch AI agents.

Method reference:

class AIBase

--connect()
--poll_server()
--run_polling_loop()
--send_data(data)
--start_polling_loop()
--stop_polling_loop()

--handle_daemon_command(raw_msg)
--run()
--start()
--stop()

--handle_response(response)

--bid(bid)
--chat(chat_msg)
--join_game(game_id, pNum)
--play(card_val)
--request_new_game()

--decode_card(card_code)
--is_legal_bid(bid)
--is_legal_play(card)

--act()


TODO:
    - have 'thinking' timeout value (halt thinking after certain interval)
    --- mandate a timeout; can be a Timer call to change a loop value & publish
    --- can specify timeout in this file? want all agent models equal in this
    - if AI are allowed to use DB, impl methods here
    
"""
from multiprocessing import Pipe
from _thread import start_new_thread
from time import sleep
from urllib.parse import urlencode
from http.client import HTTPConnection
from json import loads as json_loads
from math import floor

import logging
log = logging.getLogger(__name__)

from core.cards import RANKS_SHORT, SUITS_SHORT, NUM_RANKS

# Settings
SERVER_HOST = "localhost"
SERVER_PORT = 2424
SERVER_URL = "{0}:{1}".format(SERVER_HOST, SERVER_PORT)

COMET_DELAY = 3.0 # Seconds to wait between successive Comet polls
# Not currently used
THINKING_TIMEOUT = 10.0 # Secs to allow AI to think before demanding response

# Constants
EVENT_NEW_GAME = 0      # Integer constants for error handling
EVENT_JOIN_GAME = 1     #
EVENT_BID = 2           #
EVENT_PLAY = 3          #

# Hardcoded values to increase performance in decoding cards

NUM_TEAMS = 2
NUM_PLAYERS = 4

GAME_UPDATE_KEYS = ['trp', 'playC', 'remP', 'sco', 'win', 'dlr', 'addC','mode']
GAMESTATE_KEYS = ['mode','trump','dealer','high_bid','declarer',
                  'actor', 'active_player','cip','scores',
                  'team_stacks']

class BareGameState:
    """Basic game state object."""
    def __init__(self):
        for key in GAMESTATE_KEYS: # Initialize empty values
            setattr(self, key, -1)
        
        self.cip = []
        self.scores = (0, 0)
        self.team_stacks = ([], []) # Defined for 2-team game

class AIBase:
    """Common features of all Cinch AI Agents."""
    
    ####################
    # Agent Management -- Creation/maintenance of Agent; metagame functions
    ####################

    def __init__(self, pipe, identity):
        # Instance variables
        self.uid = 0
        self.manager = None
        self.running = False
        self.pipe = pipe # type = multiprocessing.Pipe
        self.name = identity['name']
        self.label = self.name

        # Network comm
        self.conn = {}
        self.connect()
        self.comet_enabled = False

        # Game
        self.in_game = False
        self.pNum = -1
        self.hand = []

        # Game state
        self.gs = BareGameState()

        log.info("{0}AI loaded".format(self.name))
        
    def __del__(self):
        """Safely shutdown AI Agent subprocess."""
        # Kill Comet server connection
        self.stop_polling_loop()
        try:
            for conn in self.conn.values():  conn.close()
        except:
            log.debug("Failed to close active conn; "
                      "may have been closed elsewhere or finished naturally.")
        finally:
            # Halt daemon loop
            self.running = False

        #TODO - log final state?

    ####################
    # Network communications -- message exchange with game server
    ####################
    
    def connect(self):
        """Create HTTP connections to Comet server.

        Using different connection for polling and posting prevents issues
        (e.g. trying to send data via post while the comet connection open).

        """
        self.conn['comet'] = HTTPConnection(SERVER_URL, timeout=10)
        self.conn['post'] = HTTPConnection(SERVER_URL, timeout=10)

    def poll_server(self):
        """Do single Comet-style GET request for new messages on Comet server.

        """
        # Comet request format
        req = "/?uid={0}".format(self.uid)

        self.conn['comet'].request("GET", req)

        res = self.conn['comet'].getresponse()
        data = res.read()

        try:
            return json_loads(data.decode())
        except ValueError:  # No JSON object to decode
            return None

    def run_polling_loop(self):
        """Polling loop execution."""
        poll = self.poll_server
        handle = self.handle_response
        
        while self.comet_enabled:
            try:
                response = poll()
                if response is not None:
                    handle(response)

            except Exception: # Wait longer for connection to finalize 
                sleep(3)
        
    def send_data(self, data):
        """Send data via POST request to Comet server.

        Any response to the request will be handled by the caller.

        data (dict): information to send to server

        """
        params = urlencode(data)
        headers = {"Content-type": "application/x-www-form-urlencoded",
                    "Accept": "text/plain"}
        self.conn['post'].request("POST", "", params, headers)       
        res = self.conn['post'].getresponse()
        data = res.read()
        
        try:
            return json_loads(data.decode())
        except ValueError:  # No JSON object to decode
            return None

    def start_polling_loop(self):
        """Begin Comet polling loop."""
        if self.comet_enabled:  # Prevent multiple simultaneous polling loops
            return
        if not self.in_game:    # Don't waste resources if not in game
            log.debug("Agent not in-game; don't start polling loop.")
            return
        
        self.comet_enabled = True
        start_new_thread(self.run_polling_loop, ())
        
    def stop_polling_loop(self):
        """Terminate Comet polling loop."""
        self.comet_enabled = False

    ####################
    # Daemon interface -- Comms. with AI Agent Manager & daemon features
    ####################

    def handle_daemon_command(self, command):
        """Process command from AI Manager sent via pipe.

        Supported commands:
        - Request new game [request_new_game(self)]
        - Join existing game [join_game(self, game_id, pNum)]
        - Shutdown [stop(self)]

        raw_msg (tuple of ints): data sent by Manager with following values:
        - (1,)        New Game
        - (2,x,y)    Join Game #x in Seat y
        - (-1,)      Shutdown

        """
        op = command[0]

        if op == -1: # Shutdown
            log.info("AI Agent {0} received shutdown command".format(
                        self.label))
            self.stop()
            self.stop_polling_loop()

        elif op == 2: # Join Game
            if self.join_game(command[1], command[2]):
                self.start_polling_loop() # Join game was successful

        elif op == 1: # New Game
            if self.request_new_game():
                self.start_polling_loop() # New game was successful

        else:
            log.warn("Unknown daemon command: {0}".format(op))

    def run(self):
        # Read from pipe -- does block ai thread, but start() is final action
        readline = self.pipe.recv # Function reference for speed++
        handle_daemon_command = self.handle_daemon_command
        
        while self.running:
            try:
                data = readline()
                handle_daemon_command(data)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.stop()
                log.exception("Killing daemon loop...")
                return

    def start(self):
        log.debug("AI Agent {0} listening on Manager pipe".format(self.label))
        self.running = True
        self.run()

    def stop(self):
        log.debug("AI Agent {0} stopped listening on Manager pipe"
                  "".format(self.label))
        self.running = False

    ####################
    # Message Receivers -- Handlers for received messages
    ####################

    def handle_response(self, response):
        """Handle response from Comet request, e.g. update internal game state.
        
        response (dict): message from Comet server of form
            {'new': int, 'msgs': list of dicts}

        """
        gs = self.gs
        for msg in response['msgs']:
            if all(k in msg for k in ['uNum','msg']): # Chat msg signature
                pass
            else: # Process updates to game state
                # Handle active player update first; other keys may make use
                # of new active player / prev. player values

                # Will raise KeyError if no actvP key
                try:  self.activate_player(msg.pop('actvP'))
                except KeyError: pass
                
                # Message needs to be divided based on 'order of operations'
                # so that certain keys are processed first
                keys = list(msg.keys())
                
                # Must remove card from hand before adding new cards to hand
                # so if present, do `playC` before `addC`
                if 'addC' in keys:  keys.append(keys.pop(keys.index('addC')))

                # Must put into play card that ends trick before clearing board
                # so if present, do `playC` before `remP`
                if 'remP' in keys:  keys.append(keys.pop(keys.index('remP')))

                # Process each key in revised order
                for key in keys:
                    val = msg[key]

                    if key == 'playC':
                        gs.cip.append(val)

                        # If I am prev. player, then I just played
                        if msg['actor'] == self.pNum:
                            self.hand.remove(val)
                            
                    elif key == 'remP':
                        team_num = val % NUM_TEAMS
                        gs.team_stacks[team_num].extend(gs.cip)
                        gs.cip = []

                    elif key == 'bid':
                        # Update high bid if needed
                        gs.high_bid = max(val, gs.high_bid)
                        gs.declarer = msg['actor']

                    elif key == 'addC': # Setup for new hand
                        self.hand = val
                        gs.team_stacks = ([], [])
                        gs.high_bid = 0

                    elif key == 'mode':  gs.mode = val

                    elif key == 'trp':  gs.trump = val

                    elif key == 'sco':  gs.scores = val

                    elif key == 'dlr':  gs.dealer = val

                    elif key == 'win':
                        # finalize log & shutdown
                        gs.mode = -1 #TODO handle End of Game
                        log.info("Game ending, {0} shutting down".format(
                                self.label))
                        self.handle_daemon_command((-1,)) # Force tuple

                    else:
                        # See docstring for handle_other_key
                        self.handle_other_key(val)

        self.gs = gs

        try:            
            self.act()
        except Exception as e:
            log.exception(e)

    def handle_other_key(self, val):
        '''Override this method within each agent's core.py as desired. This 
        is to be used to handle message keys that are ignored by base.py (e.g.
        scores, player names). If ignored keys are being handled in identical 
        ways by all agents in their handle_other_key overrides, refactor to 
        include that functionality in handle_response().
        
        val (str): message key

        '''
        pass
        
    ####################
    # Message Transmitters -- Convenience methods for sending messages
    ####################

    def bid(self, bid):
        """Send bid to server. Handle error response.

        bid (int): bid value (0-5), assumed to have been legality checked

        """
        res = self.send_data({'uid':self.uid, 'bid':bid}) # Expects nothing

        # Bid may be illegal anyway
        if res:
            log.error("Agent made illegal bid of {0}; adjusting bid to PASS."
                        "".format(bid))
            self.bid(0) # Pass
        else:
            if bid > 0:
                log.info("{0} bids {1}".format(self.label, bid))
            else:
                log.info("{0} passes".format(self.label))

    def chat(self, chat_msg):
        """Send chat-style message to Comet server (for debugging & hijinks).

        chat_msg (str): message to send via chat channels

        """
        self.send_data({'uid':self.uid, 'msg':chat_msg})


    def join_game(self, game_id, pNum):
        """Instruct Agent to attempt to join game.

        game_id (int): id of target game
        pNum (int): desired seat in game
        
        """
        if self.in_game:    # Prevent in-game client from starting new game
            return
        
        data = {'join': game_id, 'pNum': pNum, 'name': "{0}/{1}".format(
                self.identity['name'], pNum)}
        res = self.send_data(data) # Expects {'uid', 'pNum'} or {'err'}

        if 'err' in res:
            log.error("Error joining game: {0}".format(res['err']))
            return False
        else:
            self.uid, self.pNum = res['uid'], res['pNum']
            self.label = "{0}/{1}".format(self.name, self.pNum)
            self.in_game = True
            self.chat("AI Agent in seat #{0}.".format(self.pNum))
            return True

    def play(self, card_val):
        """Send proposed play to server. Handle error response.

        card_val (int): int encoding of card, assumed to have been legality
            checked already

        """
        res = self.send_data({'uid':self.uid, 'card':card_val}) # Expects null

        # Play may be deemed illegal by server anyway
        if res:
            # No fallback option defined for an illegal play
            log.error("{1} made illegal play with card_val {0}"
                        "".format(self.print_card(card_val), self.label))
        else:
            log.info("{0} plays {1}".format(self.label, 
                                            self.print_card(card_val)))
    
    def request_new_game(self):
        """Instruct Agent to request new game from server. Used only for 
        AI-only games.
        
        plrs (string): CSV agent model num list 
        
        """
        if self.in_game:    # Prevent in-game client from creating new game
            return

        # It thinks it's people (Manager will take care of the players)
        data = {'game':0, 'plrs':"-3,-3,-3,-3", 'name': "{0}/0".format(
                self.identity['name'])}
        res = self.send_data(data) # Expected return is {'uid', 'pNum'}

        if 'err' in res:
            log.error("Error requesting new game.")
            return False
        else:
            self.uid, self.pNum = res['uid'], res['pNum']
            self.label = "{0}/{1}".format(self.name, self.pNum)
            self.in_game = True
            self.chat("AI Agent in seat #{0}.".format(self.pNum))
            return True

    ####################
    # Game Rules -- Adapted versions of core game functionality
    ####################

    def activate_player(self, actvP):
        """Advance active player value to actvP."""
        self.gs.active_player = actvP

    def decode_card(self, card_code):
        """Decode card encoding into (rank, suit) pair."""
        suit = floor((card_code - 1) / NUM_RANKS)
        rank = card_code - (suit * NUM_RANKS) + 1
        
        return rank, suit # rank and suit are integers
        
    def encode_card(self, rank, suit):
        """Encode rank,suit pair into integer in range 1-52.
        
        rank (int), suit (int): rank and suit of card to encode.
        
        """
        return (rank-1) + (suit*NUM_RANKS)

    def print_card(self, card_code):
        """Return descriptive string of card; copies Card.__repr__() method."""

        suit = (card_code-1) // NUM_RANKS
        rank = card_code - suit*NUM_RANKS + 1

        return "{r}{s}".format(r=RANKS_SHORT[rank], s=SUITS_SHORT[suit])
        
    def is_legal_bid(self, bid):
        """Check if proposed bid is legal.

        bid (int): bid value (0=PASS, 5=CINCH)

        """
        if bid == 0:
            return True # Always legal to pass
        elif bid < 0 or bid > 5:
            return False # Bid out of bounds
        elif bid > self.gs.high_bid:
            return True
        elif bid == 5 & self.pNum == self.gs.dealer:
            return True
        else:
            return False

    def is_legal_play(self, card):
        """Check if proposed play is legal.

        card (int): card code of proposed play

        """
        gs = self.gs
        decode = self.decode_card

        if len(gs.cip) == 0:
            return True # No restriction on what can be led
        else:
            _, suit = decode(card)
            if suit == gs.trump:
                return True # Trump is always OK
            else:
                _, led = decode(gs.cip[0])
                if suit == led:
                    return True # Followed suit
                else:
                    for c in self.hand:
                        if led == decode(c)[1]:
                            return False # Could've followed suit but didn't

                    return True # Throwing off
    
    def get_legal_plays(self, as_card_objects=False):
        """Create subset of hand of legal plays."""
        card_vals = list(filter(self.is_legal_play, self.hand))
        
        if as_card_objects:
            objs = []
    
            for val in card_vals:
                r, s = self.decode_card(val)
                objs.append(MyCard(val, r, s))
            return objs
            
        else:
            return card_vals
        
    def get_winning_card(self, cards_in_play, card_led):
        """Return the card that wins a trick with cards_in_play. Used to
        evaluate outcome of potential plays.
        
        cards_in_play (list): list of card objects in a trick
        card_led (MyCard object): card led that trick (also in in cards_in_play)
        
        """
        trump = self.gs.trump
        
        # Determine winning suit (either trump or suit led)
        winning_suit = card_led.suit
        for card in cards_in_play:
            if trump == card.suit:
                winning_suit = trump
                break

        cur_highest_rank = 0
        for card in cards_in_play:
            #print(card, card.__class__)
            if card.suit == winning_suit:
                if card.rank > cur_highest_rank:
                    cur_highest_rank = card.rank
                    cur_highest_card = card

        return cur_highest_card

    ####################
    # Intelligence -- Implement in subclasses
    ####################

    def act(self):
        """Initiate action.

        Called after processing each message block from Comet server.
        Typical implementation is to check if AI is active player, and if so,
        trigger the appropriate action (bid or play) and related analysis.

        This is called regardless of who is active player. This allows, for
        example, the AI to do preliminary play analysis before its own turn.
        Subclasses are responsible for performing any needed checks.

        Also, the current game mode should be considered.

        """
        raise NotImplementedError("act() needs to be implemented in subclass.")


class MyCard:
    # Helper class for organizing cards. Moved to base.py as this (or something
    # like this) is going to be essential for all AIs.
    def __init__(self, val, rank, suit):
        # val, rank, and suit are all integers
        self.val = val
        self.rank = rank
        self.suit = suit
        
    def __repr__(self):
        return "{1}{2} ({0})".format(self.val, RANKS_SHORT[self.rank],
                                     SUITS_SHORT[self.suit])
##############
# Important
##############
#
# The "__main__" function must be empty for base.py for final implementation.
#
