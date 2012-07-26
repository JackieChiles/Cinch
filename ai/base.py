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

--handle_error(event, err_msg)
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
    - redirect print-statements elsewhere (log file?) -- pending logging
    - have 'thinking' timeout value (halt thinking after certain interval)
    --- mandate a timeout; can be a Timer call to change a loop value & publish
    --- can specify timeout in this file? want all agent models equal in this
    - if AI are allowed to use DB, impl methods here
    
"""
import multiprocessing

from _thread import start_new_thread
from time import sleep
import urllib.parse
from http.client import HTTPConnection
import json
from sys import stdin # for listening to Manager
from os import name as osname

# Settings
SERVER_HOST = "localhost"
SERVER_PORT = 2424
SERVER_URL = "{0}:{1}".format(SERVER_HOST, SERVER_PORT)

COMET_DELAY = 3.0 # Seconds to wait between successive Comet polls
# Not currently used
THINKING_TIMEOUT = 10.0 # Secs to allow AI to think before demanding response

# Constants
EVENT_NEW_GAME = 0      # integer constants for error handling
EVENT_JOIN_GAME = 1     #
EVENT_BID = 2           #
EVENT_PLAY = 3          #

# Card values used for logging
RANKS_SHORT = {2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9',
               10:'T', 11:'J', 12:'Q', 13:'K', 14:'A'}
# Code to support deprecated/legacy development platforms:
if osname == 'nt':
    SUITS_SHORT = {0:'C', 1:'D', 2:'H', 3:'S'}
else:
    SUITS_SHORT = {0:'\u2663', 1:'\u2666', 2:'\u2665', 3:'\u2660'}

# Hardcoded values to increase performance in decoding cards
SUIT_TERMS = [0,13,26,39]
RANKS = range(2,15)
NUM_RANKS = 13

NUM_TEAMS = 2
NUM_PLAYERS = 4

GAME_UPDATE_KEYS = ['trp', 'playC', 'remP', 'sco', 'win', 'dlr', 'addC','mode']
GAMESTATE_KEYS = ['mode','trump','dealer','high_bid','declarer',
                  'previous_player','active_player','cip','scores',
                  'team_stacks']


class AIBase:
    """Common features of all Cinch AI Agents."""
    
    ####################
    # Agent Management -- Creation/maintenance of Agent; metagame functions
    ####################

    def __init__(self, pipe=None):#TODO: cleanup/make better
        # Instance variables
        self.uid = 0
        self.manager = None
        self.running = False
        self.pipe = pipe
        
        # Network comm
        self.conn = {}
        self.connect()
        self.comet_enabled = False

        # Game
        self.in_game = False
        self.pNum = -1
        self.hand = []

        # Game state
        gs = {}
        for key in GAMESTATE_KEYS:  gs[key] = -1 # Initialize gs
        gs['cip'] = []
        gs['scores'] = [0,0]    # Defined for 2-team game
        gs['team_stacks'] = [[],[]]
        self.gs = gs

    def __del__(self):
        """Safely shutdown AI Agent subprocess."""
        # Kill Comet server connection
        self.stop_polling_loop()
        try:
            for conn in self.conn.values():  conn.close()
        except:
            print("cant stop conns")
        finally:
            # Halt daemon loop
            self.running = False

        #TODO
        #log final state?

    ####################
    # Network communications -- message exchange with game server
    ####################
    
    def connect(self):
        """Create HTTP connections to Comet server.

        Using different connection for polling and posting prevents issues
        (e.g. trying to send data via post while the comet connection open).

        """
        self.conn['comet'] = HTTPConnection(SERVER_URL)
        self.conn['post'] = HTTPConnection(SERVER_URL)

    def poll_server(self):
        """Do single Comet-style GET request for new messages on Comet server.

        """
        # Comet request format
        req = "/?uid={0}".format(self.uid)

        self.conn['comet'].request("GET", req)

        res = self.conn['comet'].getresponse()
        data = res.read()

        try:
            return json.loads(data.decode())
        except ValueError:  # No JSON object to decode
            return None

    def run_polling_loop(self):
        """Polling loop execution."""
        poll = self.poll_server
        handle = self.handle_response
        
        while self.comet_enabled:
            try:
                response = poll()
                if response is not None: #TODO try-catch this better/faster
                    handle(response)

            except Exception: # Wait longer for connection to finalize 
                sleep(COMET_DELAY/2)
        
    def send_data(self, data):
        """Send data via POST request to Comet server.

        Any response to the request will be handled by the caller.

        data (dict): information to send to server

        """
        params = urllib.parse.urlencode(data)
        headers = {"Content-type": "application/x-www-form-urlencoded",
                    "Accept": "text/plain"}
        self.conn['post'].request("POST", "", params, headers)       
        res = self.conn['post'].getresponse()
        data = res.read()
        
        try:
            return json.loads(data.decode())
        except ValueError:  # No JSON object to decode
            return None

    def start_polling_loop(self):
        """Begin Comet polling loop."""
        if self.comet_enabled:  # Prevent multiple simultaneous polling loops
            return
        if not self.in_game:    # Don't waste resources if not in game
            print("Agent not in-game; don't start polling loop.")
            return
        
        self.comet_enabled = True
        start_new_thread(self.run_polling_loop, ())
        
    def stop_polling_loop(self):
        """Terminate Comet polling loop."""
        self.comet_enabled = False

    ####################
    # Daemon interface -- Comms. with AI Agent Manager & daemon features
    ####################

    def handle_daemon_command(self, raw_msg):
        """Process command from AI Manager.

        Supported commands:
        - Request new game [request_new_game(self)]
        - Join existing game [join_game(self, game_id, pNum)]
        - Shutdown [stop(self)]

        raw_msg (str): raw data sent by Manager with the following values:
        - '1'       New Game
        - '2|x|y'   Join Game #x in Seat y
        - '-1'      Shutdown

        """
        print('msg=', raw_msg)
        msg = raw_msg.split("|")
        try:
            m_type = int(msg[0])
        except ValueError:
            if raw_msg == "": # Manager died
                self.stop()
                return
            else:
                print("invalid daemon msg:", raw_msg)
                return

        if m_type == -1: # Shutdown (most common)
            self.stop()

        elif m_type == 2: # Join Game
            if self.join_game(int(msg[1]), int(msg[2])):
                self.start_polling_loop() # Join game was successful

        # This option is currently inactive, as new game requests require a 'plrs' parameter now
        elif m_type == 1: # New Game
            if self.request_new_game():
                self.start_polling_loop() # New game was successful

        else: # Unhandled m_type
            print(m_type)

    def run(self):
        # Read from pipe -- does block, but start() is final action in init
        readline = self.pipe.recv #function pointer-ish
        handle_daemon_command = self.handle_daemon_command
        
        while self.running:
            try:
                data = readline()
                handle_daemon_command(data)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.stop()
                raise

    def start(self):
        self.running = True
        self.run()

    def stop(self):
        self.running = False

    ####################
    # Message Receivers -- Handlers for received messages
    ####################
   
    def handle_error(self, event, err_msg): #TODO pending logging UI
        """Handler for error messages received from Comet server.

        event (int): descriptor for source of error
        err_msg (str): body of error message

        """
        if event == EVENT_PLAY:
            print("ERROR", err_msg)
        elif event == EVENT_BID:
            print("ERROR", err_msg)
        elif event == EVENT_JOIN_GAME:
            print("ERROR", err_msg)
        elif event == EVENT_NEW_GAME:
            print("ERROR", err_msg)
        else:
            #unidentified error
            pass

    def handle_response(self, response):
        """Handle response from Comet request, e.g. update internal game state.
        
        TODO:Avoid having handler output to stdout in final build. Log instead.

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
                        gs['cip'].append(val)

                        # If I am prev. player, then I just played
                        if gs['previous_player'] == self.pNum:
                            self.hand.remove(val)
                            
                    elif key == 'remP':
                        team_num = val % NUM_TEAMS
                        gs['team_stacks'][team_num].extend(gs['cip'])
                        gs['cip'] = []

                    elif key == 'bid':
                        # Update high bid if needed
                        gs['high_bid'] = max(val, gs['high_bid'])
                        gs['declarer'] = gs['previous_player']

                    elif key == 'addC': # Setup for new hand
                        self.hand = val
                        gs['team_stacks'] = [[], []]
                        gs['high_bid'] = 0

                    elif key == 'mode':  gs['mode'] = val

                    elif key == 'trp':  gs['trump'] = val

                    elif key == 'sco':  gs['scores'] = val

                    elif key == 'dlr':  gs['dealer'] = val

                    elif key == 'win':
                        # finalize log & shutdown
                        gs['mode'] = -1 #TODO handle End of Game
                        print("AI Ending Game")
                        self.handle_daemon_command("-1")

                    else:  #TODO add support for mp, gp keys
                        pass
                        # print("!!unhandled key:", key)
                        # Uncomment to test AI key handling

        self.act() # Once all updates are processed, act

    ####################
    # Message Transmitters -- Convenience methods for sending messages
    ####################

    def bid(self, bid):
        """Send bid to server. Handle error response.

        bid (int): bid value (0-5), assumed to have been legality checked

        """
        res = self.send_data({'uid':self.uid, 'bid':bid}) # Expects nothing

        #Bid may be illegal anyway
        if res:
            self.handle_error(EVENT_BID, res['err'])

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

        data = {'join': game_id, 'pNum': pNum, 'name': "Mr AI"} #TODO make this use AI name declared at the Agent-level init.py
        res = self.send_data(data) # Expects {'uid', 'pNum'} or {'err'}

        if 'err' in res:
            self.handle_error(EVENT_JOIN_GAME, res['err'])
            return False
        else:
            self.uid, self.pNum = res['uid'], res['pNum']
            self.in_game = True
            self.chat("AI Agent in seat #{0}.".format(self.pNum))
            return True

    def play(self, card_val):
        """Send proposed play to server. Handle error response.

        card_val (int): int encoding of card, assumed to have been legality
            checked already

        """
        res = self.send_data({'uid':self.uid, 'card':card_val}) # Expects null

        #Play may be deemed illegal by server anyway
        if res:
            self.handle_error(EVENT_PLAY, res['err'])
        
    def request_new_game(self):
        """Instruct Agent to request new game from server."""
        if self.in_game:    # Prevent in-game client from creating new game
            return

        data = {'game': 0}
        res = self.send_data(data) # Expects {'uid', 'pNum'}

        if 'err' in res:
            self.handle_error(EVENT_NEW_GAME, res['err'])
            return False
        else:
            self.uid, self.pNum = res['uid'], res['pNum']
            self.in_game = True
            self.chat("AI Agent in seat #{0}.".format(self.pNum))
            return True

    ####################
    # Game Rules -- Adapted versions of core game functionality
    ####################

    def activate_player(self, actvP):
        """Advance active player value to actvP."""
        self.gs['previous_player'] = self.gs['active_player']
        self.gs['active_player'] = actvP

    def decode_card(self, card_code): #TODO: make this better
        """Convert card code into rank, suit pair."""
        val = card_code+1
        for term in SUIT_TERMS:
            if val-term in RANKS:
                return val-term, int(term/NUM_RANKS)
        return -1, -1

    def print_card(self, card_code):
        """Return descriptive string of card; copies Card.__repr__() function."""

        suit = (card_code-1) // NUM_RANKS
        rank = card_code - suit*NUM_RANKS + 1

        return "{r}{s}".format(r=RANKS_SHORT[rank], s=SUITS_SHORT[suit])
        
    def is_legal_bid(self, bid):
        """Check if proposed bid is legal.

        bid (int): bid value (0=PASS, 5=CINCH)

        """
        if bid == 0:
            return True # always legal to pass
        elif bid < 0 or bid > 5:
            return False # bid out of bounds
        elif bid > self.gs['high_bid']:
            return True
        elif bid == 5 & self.pNum == self.gs['dealer']:
            return True
        else:
            return False

    def is_legal_play(self, card):
        """Check if proposed play is legal.

        card (int): card code of proposed play

        """
        gs = self.gs
        decode = self.decode_card

        if len(gs['cip']) == 0:
            return True # No restriction on what can be led
        else:
            _, suit = decode(card)
            if suit == gs['trump']:
                return True # Trump is always OK
            else:
                _, led = decode(gs['cip'][0])
                if suit == led:
                    return True # Followed suit
                else:
                    for c in self.hand:
                        if led == decode(c)[1]:
                            return False # Could've followed suit but didn't

                    return True # Throwing off

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
    
##############
# Important
##############
#
# The "__main__" function must be empty for base.py for final implementation.
#
