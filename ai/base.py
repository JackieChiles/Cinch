#!/usr/bin/python2

"""Base functionality for Cinch AI agents.

AIBase is designed to handle all the functionality common across possible AI
models, including socketio communications, game state management, and bid/play
legality checking. This should leave AI subclass designers free to focus on the
actual gameplay intelligence.

TODO fix bug that allows AI to make play that is called illegal by server
TODO add handler for 'win' message to allow for post-mortem analysis
TODO monitor log when multi-AI games end; used to get 'exit' message race
  condition so was using sleep() during stop(), but have removed

Attributes:
  log (Logger): Log interface common to all Cinch modules.
  NUM_TEAMS (int): Hardcoded team count, made available for AI models.
  NUM_PLAYERS (int): Hardcoded player count, made available for AI models.
  BID (int): Mode number for bidding.
  PLAY (int): Mode number for playing.

Public classes:
  GS: Generic object for managing game states.
  AIBase: Base class for AI models to extend/inherit.

"""

import logging
log = logging.getLogger(__name__)

# Add parent directory (/cinch/) to Python path for imports
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collections import defaultdict
from socketIO_client import SocketIO, BaseNamespace

import core.cards as cards
from common import SOCKETIO_PORT, SOCKETIO_NS

NUM_TEAMS = 2
NUM_PLAYERS = 4
BID = 2
PLAY = 1


class GS(object):
    """Container for game state properties.

    This is mainly to allow AI to reference game state properties with the
    dot operator instead of with dictionary keys.

    """
    def __init__(self):
        """Initialize data fields for the gamestate."""
        self.reset()

    def __repr__(self):
        """Return string for representing game state."""
        val = ""
        public_props = (name for name in dir(self) if not name.startswith('_'))
        for name in public_props:
            if name != "reset":
                val += name + ": " + str(getattr(self, name)) + "\n"
        return val

    def reset(self):
        """Initialize or clear certain fields for gamestate data."""
        self.cardsInPlay = list()
        self.bidLog = dict()
        self.takenCards = defaultdict(list)
        self.highBid = -1


class AIBase(object):
    """Common features of all Cinch AI Agents.

    This provides an interface with the socketio server, handles known socket
    event messages, and includes common functions like checking play legality.

    When the agent receives indication that it is the active player, the play
    or bid methods are called, which must return the AI's desired play/bid.

    Attributes:
      room (int): The room number that the agent is in.
      pNum (int): The player number / seat number occupied by the agent.
      hand (list): The agent's hand of Card objects.
      gs (GS): The gamestate object used by the agent.
      name (str): The agent's name as identified in the model module.
      label (str): The label used to identify the agent in logs.
      socket (SocketIO): The socketio connection used to communicate with the
        main server.
      ns (BaseNamespace): The namespace used by the socket.

    """
    # ===============
    # Agent Management & Communications
    # ===============
    def __init__(self, targetRoom, targetSeat, ident):
        """Initialize AI.

        The AI agent connects to the server, joins a game, and prepares to
        receive game data.

        Args:
          targetRoom (int): Target game room number.
          targetSeat (int): Target seat within game room.
          ident (dict): AI identifying info, including data like version number
            and AI description. This is provided from the AI model module via
            the manager.

        """
        self.room = None
        self.pNum = None
        self.hand = []
        self.gs = GS()
        self.name = ident['name']
        self.label = self.name + "_" + str(targetSeat)

        self.setupSocket()
        self.ns.emit('nickname', self.label)
        self.join(targetRoom, targetSeat)
        self.pNum = targetSeat

    def __del__(self):
        """Cleanly shutdown AI agent."""
        self.stop()

    def ackJoin(self, *args):
        """Callback for request to join room.

        Args:
          *args (list): Confirmation data after joining room. If successful,
            this will be a 1-element list with a dict containing `roomNum`,
            `seatChart`, and `mySeat` keys. Otherwise, it will be an empty list
            because the request resulted in an error.

        """
        if len(args) == 0:
            # The agent will receive an 'err' event in this case.
            # TODO: look into intelligently handling this kind of error and
            # ensure it is not possible to sit in a bad seat.
            self.stop()
            return

        data = args[0]
        self.room = data['roomNum']

        if self.room != 0:  # Joining the lobby doesn't warrant any action
            self.pNum = data['mySeat']
            log.info("{2}_AI joined Game {0} Seat {1}".format(
                self.room, self.pNum, self.name))

    def on_err(self, msg):
        """Handle error event from server and log all data.

        Since some errors may be non-fatal, an error does not kill the agent.

        Args:
          msg (str): Error message.

        """
        log.error("err: {0}".format(msg))
        log.error("dump: {0} {1}".format(self.label, str(self.hand)))
        log.error("gs: {0}".format(self.gs))

    def handle_game_action(self, *args):
        """Combination handler for bid and play.

        This calls the agent's `bid` or `play` method as appropriate. If it is
        not the agent's turn, the `think` method is called instead. If the game
        is over, no actions are taken.

        This is also called when receiving `startData`.

        Args:
          *args (list): Data transmitted by server with bid or play event.

        """
        try:
            msg = args[0]
        except Exception as e:
            log.error("{0}: {1}".format(e.message, args))
            return

        self.applyUpdate(msg)

        if 'win' in msg:  # Game is over
            return

        if self.gs.activePlayer == self.pNum:
            if self.gs.mode == BID:
                self.bid()
            else:
                self.play()
        else:
            self.think()

    def setupSocket(self):
        """Create socket connection and configure namespace."""
        self.socket = SocketIO('127.0.0.1', SOCKETIO_PORT)
        self.ns = self.socket.define(BaseNamespace, SOCKETIO_NS)

        self.ns.on('err',       self.on_err)
        self.ns.on('bid',       self.handle_game_action)
        self.ns.on('play',      self.handle_game_action)
        self.ns.on('startData', self.handle_game_action)

    def applyUpdate(self, msg):
        """Update internal game information based on server message.

        Args:
          msg (dict): Message from server containing game state information
            and changes.

        """
        self.gs.activePlayer = msg['actvP']

        if 'win' in msg:
            self.stop()

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
            self.hand = [cards.Card(num) for num in msg['addC']]
            self.gs.reset()

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

        Args:
          room (int): Target room number
          seat (int): Target seat number

        """
        self.ns.emit('join', room, seat, self.ackJoin)

    def start(self):
        """Activate AI."""
        self.socket.wait()  # Blocks until self.stop()

    def stop(self):
        """Gracefully shutdown AI agent."""
        self.socket.disconnect()

        # TODO do any final cleanup (logging, etc)

    # ===============
    # Game Actions & Rules
    # ===============

    def send_bid(self, bid):
        """Send bid to server. Handle error response.

        TODO add callback to handle if an illegal bid was made; AIBase should
        provide failsafe methods.

        Args:
          bid (int): Bid amount (0-5, where PASS = 0)

        """
        if self.is_legal_bid(bid):
            pass
        elif bid == 0:  # Illegally tried to pass (stuck dealer)
            bid = 1
            log.error("Agent illegally tried to pass; adjusting bid to 1.")
        else:
            log.error("Agent made illegal bid of {0}; adjusting bid to PASS."
                      "".format(bid))
            bid = 0

        self.ns.emit('bid', bid)  # Transmit bid to server

        if bid > 0:
            log.info("{0} bids {1}".format(self.label, bid))
        else:
            log.info("{0} passes".format(self.label))

    def send_chat(self, chat_msg):
        """Send chat-style message to server (for debugging & hijinks).

        Args:
          chat_msg (str): Message to send via chat channels.

        """
        self.ns.emit('chat', chat_msg)

    def send_play(self, card):
        """Send proposed play to server and remove card from hand.

        If the AI sends an illegal play, there is no recovery.

        TODO: add callback to handle illegal play; AIBase should provide
        failsafe methods.

        Args:
          card (Card): Card object to play. It is assumed to have been checked
            for play legality by the caller.

        """
        card_val = card.code
        self.ns.emit('play', card_val)

        log.info("{0} plays {1}".format(self.label, str(card)))
        self.hand.remove(card)

    def is_legal_bid(self, bid):
        """Check if proposed bid is legal. Return boolean.

        Args:
          bid (int): Bid value (0=PASS, 5=CINCH).

        """
        if bid == 0:
            if self.pNum == self.gs.dealer and self.gs.highBid < 1:
                return False  # Stuck dealer, must not pass
            else:
                return True  # Always legal to pass otherwise
        elif bid < 0 or bid > 5:
            return False  # Bid out of bounds
        elif bid > self.gs.highBid:
            return True
        elif bid == 5 and self.pNum == self.gs.dealer:
            return True
        else:
            return False

    def is_legal_play(self, card):
        """Check if proposed play is legal. Return boolean.

        card (Card): Proposed play.

        """
        if len(self.gs.cardsInPlay) == 0:
            return True  # No restriction on what can be led

        if card.suit == self.gs.trump:
            return True  # Trump is always OK
        else:
            led = self.gs.cardsInPlay[0].suit
            if card.suit == led:
                return True  # Followed suit
            else:
                for c in self.hand:
                    if led == c.suit:
                        return False  # Could've followed suit but didn't

                return True  # Throwing off

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
        raise NotImplementedError(
            "play() needs to be implemented in subclass.")

    def think(self):
        """Thinking logic, optionally implemented within each agent.

        This gets called after bids/plays but when this agent is not the active
        player (e.g. for pruning move trees after a card is played).

        """
        pass
