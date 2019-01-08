#!/usr/bin/python2
"""
Joe Lowbid isn't a fan of bidding any higher than is absolutely necessary.
He behaves just like Rand AI, but will always make the lowest legal bid.
This should be welcome news to anyone frustrated by Rand's penchant for occasional
wildly optimistic bidding.

Attributes:
  * The following attributes are mandatory for all AI models. Note the double-
    underscores.
  AI_CLASS (str): The name of the AI class. This *must* match the name of the
    class that extends AIBase.
  __author__ (str): AI author/designer's name.
  __version__ (str): Version information for model.
  __date__ (str): Release date for model.
  __skill__ (str): Skill level/description of AI, used for informing AI
    selection by players.
  __agent_name__ (str): Name of AI agent. This is used for display and logging
    purposes and may differ from AI_CLASS.
  __description__ (str): Brief description of AI. This may include highlights
    of its logic, any special techniques, or other info that may be of interest
    to users.

Public classes:
  JoeLowbid: AI model for random, low-bidding gameplay.

"""

import random

# Import base class for AI agent
from ai.base import AIBase, log

AI_CLASS = "JoeLowbid"  # Set this to match the class name for the agent
__author__ = "JackieChiles"
__version__ = "1.0"
__date__ = "16 November 2014"
__skill__ = "0"
__agent_name__ = "JoeLowbid"
__description__ = "Always bid at least two? Shoot man, I ain't bidding higher than I have to."


class JoeLowbid(AIBase):
    def __init__(self, room, seat):
        """Initialize AI agent. Blocks thread.

        All agents *must* include a super() call like below, and must have
        `self.start()` as the final line of their __init__ method.

        Args:
          room (int): Target room number.
          seat (int): Target seat number within room.

        """
        super(JoeLowbid, self).__init__(room, seat, self.identity)
        self.start()  # Blocks thread

    def bid(self):
        """Overriding base class bid.

        Always makes the lowest legal bid.

        """
        # log.debug("{0} is bidding...".format(self.label))
        for bid in range(5):
            if self.is_legal_bid(bid):
                self.send_bid(bid)
                return

    def play(self):
        """Overriding base class play.

        Plays a random card from the set of legal plays it could make.

        """
        # log.debug("{0} is playing...".format(self.label))
        legal_cards = []
        for c in self.hand:
            if self.is_legal_play(c):
                legal_cards.append(c)
        chosen_card_pos = random.randint(0, len(legal_cards)-1)
        # log.debug(str(legal_cards))
        chosen_card = legal_cards[chosen_card_pos]
        self.send_play(chosen_card)

    def think(self):
        """Overriding base class think. This is optional and here to demo."""
        pass
