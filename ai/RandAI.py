#!/usr/bin/python3
"""Rand: The pesudo-random master."""

import random

# Import base class for AI agent
from ai.base import AIBase, log

AI_CLASS = "Rand" # Set this to match the class name for the agent
__author__  = "JACK!"
__version__ = "1.0"
__date__    = "8 July 2012"
__skill__   = "0"
__agent_name__  = "Rand"
__description__ = "Pseudo randomness at its best."


class Rand(AIBase):
    def __init__(self, room, seat):
        super(Rand, self).__init__(room, seat, self.identity)  # Call to parent init
        self.start() # Blocks

    def bid(self):
        """Overriding base class bid."""
        # log.debug("{0} is bidding...".format(self.label))
        r = random.random()

        if self.is_legal_bid(self.gs.highBid+1) and (r < 0.5):
            bid = self.gs.highBid+1
            self.send_bid(bid)
        else:
            self.send_bid(0)

    def play(self):
        """Overriding base class play."""
        # log.debug("{0} is playing...".format(self.label))
        legal_cards = []
        for c in self.hand:
            if self.is_legal_play(c):
                legal_cards.append(c)
        chosen_card_pos = random.randint(0,len(legal_cards)-1)
        # log.debug(str(legal_cards))
        chosen_card = legal_cards[chosen_card_pos]
        self.send_play(chosen_card)

    def think(self):
        """Overriding base class think. This is optional and here to demo."""
        pass
