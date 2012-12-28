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
    --- To devs: don't publish an AI that takes forever to do anything!
    - if AI are allowed to use DB, impl methods here
    
"""
from multiprocessing import Pipe
from _thread import start_new_thread
from time import sleep
from urllib.parse import urlencode

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
        
        self.label = self.name = identity['name']

        # Game
        self.in_game = False
        self.pNum = -1
        self.hand = [] # list of Card objects will get cloned from the Game 

        # Game state
        self.gs = None

        log.info("{0}AI loaded".format(self.name))
        
    def __del__(self):
        """Safely shutdown AI Agent subprocess."""
        # Let manager know agent is shutting down
        pass###
        
        self.running = False
        
        #TODO - log final state?

    ####################
    # Message interface
    ####################
    
    def send_data(self, data):
        """Send information to game via AI Manager pipe
        
        data (dict): data to send
        
        """
        self.queue.put(data)
                

    def handle_command(self, command):
        """Process command from input pipe.

        command (dict): data sent with following values:
        - {'cmd': some command} - a command from the AI manager
        - {'gs': (message, game)} - a message and a new game state 
         
        """
        if 'cmd' in command:
            op = command['cmd'][0]

            if op == -1: # Shutdown
                log.info("AI Agent {0} received shutdown command".format(
                            self.label))
                self.stop()
                
            elif op == 1: # New game
                self.uid = command['cmd'][1]
                self.pNum = command['cmd'][2]
            
            elif op == 4: # Queue for sending messages to AI Mgr
                self.queue = command['cmd'][1]

        elif 'gs' in command:
#            msg = command['gs'][0] ##may use for chats. everthing else should live in game
            self.game = command['gs'][1] #Will need mechanism to protect hands of other players###
            self.gs = self.game.gs

            if self.hand == []: # Need to get a new hand
                self.hand = self.game.players[self.pNum].hand
                
            self.act()
        
        else:
            log.warn("Unknown daemon command: {0}".format(str(command)))

    def run(self):
        # Read from pipe -- does block ai thread, but start() is final action
        readline = self.pipe.recv              # Function references for speed++
        handle_command = self.handle_command
        
        while self.running:
            try:
                data = readline()
                handle_command(data)
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.stop()
                log.exception("Killing daemon loop...")
                return

    def start(self, queue):
        log.debug("AI Agent {0} listening on input pipe".format(self.label))
        self.queue = queue
        self.running = True
        self.run()

    def stop(self):
        log.debug("AI Agent {0} stopped listening on input pipe"
                  "".format(self.label))
        self.running = False
        
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

    def play(self, card):
        """Send proposed play to server. Handle error response.

        card (Card): card object, assumed to have been legality checked

        """
        card_val = card.code
        res = self.send_data({'uid':self.uid, 'card':card_val}) # Expects null

        # Play may be deemed illegal by server anyway
        if res:
            # No fallback option defined for an illegal play
            log.error("{1} made illegal play with card_val {0}"
                        "".format(self.print_card(card), self.label))
        else:
            log.info("{0} plays {1}".format(self.label, 
                                            self.print_card(card)))

    ####################
    # Game Rules -- Adapted versions of core game functionality
    ####################

    def activate_player(self, actvP):
        """Advance active player value to actvP."""
        self.gs.active_player = actvP

    def print_card(self, card):
        """Return descriptive string of card; copies Card.__repr__() method."""
        return "{r}{s}".format(r=RANKS_SHORT[card.rank], s=SUITS_SHORT[card.suit])
        
    def is_legal_bid(self, bid): # try to refactor core.game to act as library for these methods
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

        card (Card): proposed play

        """
        gs = self.gs

        if len(gs.cards_in_play) == 0:
            return True # No restriction on what can be led
        else:
            if card.suit == gs.trump:
                return True # Trump is always OK
            else:
                led = gs.cards_in_play[0].suit
                if card.suit == led:
                    return True # Followed suit
                else:
                    for c in self.hand:
                        if led == c.suit:
                            return False # Could've followed suit but didn't

                    return True # Throwing off
    
    def get_legal_plays(self, as_card_objects=True):
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

