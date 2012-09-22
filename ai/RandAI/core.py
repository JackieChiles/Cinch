#!/usr/bin/python3
"""Rand: The pesudo-random master."""

import random

# Import base class for AI agent
from ai.base import AIBase, log


class Rand(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

    def act(self):
        """Overriding base class act."""
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                log.info("{0} is playing...".format(self.label))
                legal_cards = []
                for c in self.hand:
                    if self.is_legal_play(c):
                        legal_cards.append(c)
                chosen_card_pos = random.randint(0,len(legal_cards)-1)
                chosen_card = legal_cards[chosen_card_pos]
                self.play(chosen_card)

            elif self.gs['mode'] == 2: # Bid
                log.info("{0} is bidding...".format(self.label))
                r = random.random()
                if self.is_legal_bid(self.gs['high_bid']+1) and (r < 0.5):
                    bid = self.gs['high_bid']+1
                    self.bid(bid)
                else:
                    self.bid(0)
