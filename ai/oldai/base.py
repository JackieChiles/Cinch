#!/usr/bin/python3
"""Base functionality for Cinch AI agents.

Method reference:

class AIBase

--send_data(data)
--handle_daemon_command(raw_msg)
--run()
--start()
--stop()

--bid(bid)
--chat(chat_msg)
--play(card_val)

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

import logging
log = logging.getLogger(__name__)

from core.cards import RANKS_SHORT, SUITS_SHORT, NUM_RANKS

# Settings
SERVER_HOST = "localhost"
SERVER_PORT = 2424
SERVER_URL = "{0}:{1}".format(SERVER_HOST, SERVER_PORT)

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
        self.queue = None # will be a multiprocessing.Queue for sending to Mgr
        
        self.name = identity['name']
        self.label = self.name

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
        pass #TODO
        
        self.running = False
        
        #TODO - log final state?

    ####################
    # Message interface
    ####################
    
    def send_data(self, data):
        """Send information to game via AI Manager queue
        
        data (dict): data to send
        
        """
        self.queue.put(data)

    def handle_command(self, command):
        """Process command from input pipe.

        command (dict): data sent with following values:
        - {'cmd': command number (int)} - command indicator from the AI manager
        - {'gs': (message, game)} - a message and a new game state 
        
        command numbers:
            -1: shutdown
             1: enter game, includes uid and pNum

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
                self.label = "{0}/{1}".format(self.name, self.pNum)

        elif 'gs' in command:
            self.msg = command['gs'][0] # May contain chats
            self.game = command['gs'][1] # TODO: Protect hands of other players
            self.gs = self.game.gs
            self.hand = self.game.players[self.pNum].hand # Refresh hand
                
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
        log.debug("AI Agent {0} listening to Manager".format(self.label))
        self.queue = queue
        self.running = True
        self.run()

    def stop(self):
        log.debug("AI Agent {0} stopped listening to Manager"
                  "".format(self.label))
        self.running = False
        
    ####################
    # Message Transmitters -- Convenience methods for sending messages
    ####################

    def bid(self, bid):
        """Send bid to server. Handle error response.

        bid (int): bid value (0-5), assumed to have been legality checked

        """
        res = self.send_data({'uid':self.uid, 'bid':bid}) # res=None is OK

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
        res = self.send_data({'uid':self.uid, 'card':card_val}) # res=None is OK

        # Play may be deemed illegal by server anyway
        if res:
            # No fallback option defined for an illegal play
            log.error("{1} made illegal play with card_val {0}"
                        "".format(str(card), self.label))
        else:
            log.info("{0} plays {1}".format(self.label, 
                                            str(card)))
            self.hand.remove(card) # Complete play

    ####################
    # Game Rules -- Adapted versions of core game functionality
    ####################
        
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

        card (Card): proposed play

        """
        if len(self.gs.cards_in_play) == 0:
            return True # No restriction on what can be led
        else:
            if card.suit == self.gs.trump:
                return True # Trump is always OK
            else:
                led = self.gs.cards_in_play[0].suit
                if card.suit == led:
                    return True # Followed suit
                else:
                    for c in self.hand:
                        if led == c.suit:
                            return False # Could've followed suit but didn't

                    return True # Throwing off
    
    # get_legal_plays() and get_winning_card() will be reimplemented when HAL is repaired.

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

