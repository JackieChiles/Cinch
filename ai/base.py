#!/usr/bin/python2
"""Base functionality for Cinch AI agents.

Class/method reference:

class GS
- No methods (empty class)

class AIBase
- ...


"""
from collections import defaultdict
from socketIO_client import SocketIO, BaseNamespace

# Add parent directory (/cinch/) to Python path for imports
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

import time, random

import core.cards as cards
from common import SOCKETIO_PORT, SOCKETIO_NS


import logging
log = logging.getLogger(__name__)


# Hardcoded values to increase performance in decoding cards
NUM_TEAMS = 2
NUM_PLAYERS = 4

# Modes
BID = 2
PLAY = 1


class GS(object):
    """Container for game state properties."""
    def __repr__(self):
        val = ""
        public_props = (name for name in dir(self) if not name.startswith('_'))
        for name in public_props:
            val += name + ": " + str(getattr(self, name)) + "\n"

        return val


class AIBase(object):
    
    """Common features of all Cinch AI Agents."""

    # ===============
    # Agent Management & Communications
    # ===============
    
    def __init__(self, targetRoom, targetSeat, ident):
        """Connect to server, join a game, and prepare variable space.

        targetRoom -- (int) game room number for AI to join
        targetSeat -- (int) seat number within game room
        ident -- (dict) identifying info from agent file & structured by manager

        """
        # Establish socketIO connection
        self.setupSocket()
        self.room = None

        self.name = ident['name']
        self.label = self.name + "_" + str(targetSeat)
        self.ns.emit('nickname', self.label)

        # Enter room and take a seat
        self.join(targetRoom, targetSeat)
        self.pNum = targetSeat # This assumption may have to change later

        # Prepare game logic variables
        self.hand = []
        self.gs = GS() # Game state object
        self.resetGamestate()

    def __del__(self):
        """Cleanly shutdown AI agent."""
        self.stop()

    def resetGamestate(self):
        """Reset certain fields in the gamestate object."""
        self.gs.cardsInPlay = list()
        self.gs.bidLog = dict()
        self.gs.takenCards = defaultdict(list)
        self.gs.highBid = -1

    # Event handlers

    def ackJoin(self, *args):
        # Successful join request was made
        self.room = args[0]['roomNum']

        if self.room != 0:
            self.pNum = args[0]['mySeat']
            log.info("{2}_AI joined Game {0} Seat {1}".format(self.room, self.pNum, self.name))

            # TODO ensure it is NOT possible for an AI to try to sit in a bad seat

    def on_err(self, msg):
        log.debug("err: {0}".format(msg))
        log.debug("dump: {0} {1}".format(self.label,str(self.hand)))
        log.debug("gs: {0}".format(self.gs))

    def on_game_action(self, *args):
        """Combination handler for bid and play."""
        try:
            msg = args[0] # Should yield a dict
        except Exception as e:
            print 'on_game_action: ', args

        self.applyUpdate(msg)

        # Check if game is over -- msg contains 'win'
        if 'win' in msg:
            return

        # Determine if AI should be playing or bidding
        if msg['actvP'] == self.pNum:
            # Handle message based on mode
            if self.gs.mode == BID: # AI should be bidding
                self.bid()
            else: # AI should be playing
                self.play()
        else:
            self.think()

    def on_startData(self, *args):
        # Initialize internal game state
        self.applyUpdate(args[0])
        if self.gs.activePlayer == self.pNum: # I'm first to act
            self.bid()

    def setupSocket(self):
        self.socket = SocketIO('127.0.0.1', SOCKETIO_PORT)
        self.ns = self.socket.define(BaseNamespace, SOCKETIO_NS)

        # Attach socketIO event handlers 
        self.ns.on('bid',       self.on_game_action)
        self.ns.on('err',       self.on_err)
        self.ns.on('play',      self.on_game_action)
        self.ns.on('startData', self.on_startData)

    # Other management functions

    def applyUpdate(self, msg):
        """Make updates to internal game information based on msg contents.

        msg -- message from server

        This is only called (currently) in response to 'bid' and 'play' events.

        """
        self.gs.activePlayer = msg['actvP']

        if 'win' in msg:
            self.stop()
            return

        if 'playC' in msg:
            self.gs.cardsInPlay.append(cards.Card(msg['playC']))        

        if 'sco' in msg:
            self.gs.score = msg['sco']

        if 'gp' in msg:
            self.gs.gp = msg['gp']

        if 'mp' in msg:
            self.gs.mp = msg['mp']

        if 'remP' in msg:
            self.gs.takenCards[msg['remP']].append(self.gs.cardsInPlay)
            self.gs.cardsInPlay = list()

        if 'dlr' in msg:
            self.gs.dealer = msg['dlr']

        if 'addC' in msg:
            # New hand for AI
            self.hand = list()
            for num in msg['addC']:
                self.hand.append(cards.Card(num))
            
            self.resetGamestate()

        if 'trp' in msg:
            self.gs.trump = msg['trp']

        if 'mode' in msg:
            self.gs.mode = msg['mode']

        if 'actor' in msg:
            self.gs.actor = msg['actor']

        if 'bid' in msg:
            self.gs.bidLog[msg['actor']] = msg['bid']
            if msg['bid'] > self.gs.highBid:
                self.gs.highBid = msg['bid']

    def join(self, room, seat):
        """Make request to join room.

        room -- (int) room number
        seat -- (int) seat number

        """
        self.ns.emit('join', room, seat, self.ackJoin)

    def start(self):
        """Activate AI."""
        self.socket.wait() # Blocks until self.stop()

    def stop(self):
        """Gracefully shutdown AI agent."""
        # Adds random backoff before AI disconnects. This helps suppress the 
        # "SOCKET IS DEAD" exception caused by all agents quitting at once, which
        # causes a race condition when the server sends out the 'exit' events. This
        # only serves to suppress an unhandled exception. A "Failed to write closing
        # frame" message still gets printed to the DEBUG handler, though.
        time.sleep(2*random.random())
        
        self.socket.disconnect()
        # TODO do any final cleanup (logging, etc)

    # ===============
    # Game Actions & Rules
    # ===============

    def send_bid(self, bid):
        """Send bid to server. Handle error response.

        bid (int): bid value (0-5)

        """
        if self.is_legal_bid(bid):
            pass
        elif bid == 0: # Illegally tried to pass (stuck dealer)
            bid = 1
            log.error("Agent illegally tried to pass; adjusting bid to 1.")
        else:
            bid = 0
            log.error("Agent made illegal bid of {0}; adjusting bid to PASS."
                      "".format(bid))

        self.ns.emit('bid', bid) # Transmit bid to server

        if bid > 0:
            log.info("{0} bids {1}".format(self.label, bid))
        else:
            log.info("{0} passes".format(self.label))

    def send_chat(self, chat_msg):
        """Send chat-style message to server (for debugging & hijinks).

        chat_msg (str): message to send via chat channels

        """
        self.ns.emit('chat', chat_msg)

    def send_play(self, card):
        """Send proposed play to server.
        
        If the AI sends an illegal play, there is no recovery.

        card (Card): card object, assumed to have been legality checked

        """
        card_val = card.code
        res = self.ns.emit('play', card_val)

        log.info("{0} plays {1}".format(self.label, 
                                        str(card)))
        self.hand.remove(card) # Complete play

    def is_legal_bid(self, bid):
        """Check if proposed bid is legal.

        bid (int): bid value (0=PASS, 5=CINCH)

        """
        if bid == 0:
            if self.pNum == self.gs.dealer and self.gs.highBid < 1:
                return False # Stuck dealer, must not pass
            else:
                return True # Always legal to pass otherwise
        elif bid < 0 or bid > 5:
            return False # Bid out of bounds
        elif bid > self.gs.highBid:
            return True
        elif bid == 5 & self.pNum == self.gs.dlr:
            return True
        else:
            return False

    def is_legal_play(self, card):
        """Check if proposed play is legal.

        card (Card): proposed play

        """
        if len(self.gs.cardsInPlay) == 0:
            return True # No restriction on what can be led

        if card.suit == self.gs.trump:
            return True # Trump is always OK
        else:
            led = self.gs.cardsInPlay[0].suit
            if card.suit == led:
                return True # Followed suit
            else:
                for c in self.hand:
                    if led == c.suit:
                        return False # Could've followed suit but didn't
                        
                return True # Throwing off

    # ===============
    # Intelligence
    # ===============

    def bid(self):
        """Bidding logic. This is to be implemented within each agent.

        This gets called only when game mode == BID and self is active player.

        """
        raise NotImplementedError("bid() needs to be implemented in subclass.")

    def play(self):
        """Play logic. This is to be implemented within each agent.

        This gets called only when game mode == PLAY and self is active player.

        """
        raise NotImplementedError("play() needs to be implemented in subclass.")

    def think(self):
        """Thinking logic. This is to be optionally implemented within each agent.

        This gets called after bids/plays but self is not the active player
        (e.g. for pruning move trees after a card is played).

        """
        pass


# TODO test is_legal_bid due to change in first case
# TODO fix bug that allows AI to make play that is called illegal by server




