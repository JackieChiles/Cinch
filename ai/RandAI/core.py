#!/usr/bin/python3
"""Rand: The pesudo-random master."""

import random

# Import base class for AI agent
from ai.base import AIBase, log


class Rand(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

        log.info("{0}AI loaded".format(self.name))

    def act(self):
        """Overriding base class act."""
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                log.info("{0} {1} is playing...".format(self.name, self.pNum))
                legal_cards = []
                for c in self.hand:
                    if self.is_legal_play(c):
                        legal_cards.append(c)
                chosen_card = random.randint(0,len(legal_cards)-1)
                self.play(legal_cards[chosen_card])
                log.info("{0} {1} plays {2}".format(
                        self.name, self.pNum, self.print_card(c)))

            elif self.gs['mode'] == 2: # Bid
                log.info("{0} {1} is bidding...".format(self.name, self.pNum))
                r = random.random()
                if self.is_legal_bid(self.gs['high_bid']+1) and (r < 0.5):
                    bid = self.gs['high_bid']+1
                    self.bid(bid)
                    log.info("{0} {1} bids {2}".format(
                            self.name, self.pNum, bid))
                else:
                    self.bid(0)
                    log.info("{0} {1} passes.".format(self.name, self.pNum))
