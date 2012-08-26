#!/usr/bin/python3
"""Wilbur: everyone's favorite hapless cinching AI."""

import random

# Import base class for AI agent
from ai.base import AIBase, log


class Wilbur(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

        log.info("{0}AI loaded".format(self.name))

    def act(self):
        """Overriding base class act."""
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                log.info("{0} {1} is playing...".format(self.name, self.pNum))
                # Play last legal card (opposite of Dave)
                for c in reversed(self.hand):
                    if self.is_legal_play(c):
                        self.play(c)
                        log.info("{0} {1} plays {2}".format(
                                self.name, self.pNum, self.print_card(c)))
                        break

            elif self.gs['mode'] == 2: # Bid
                log.info("{0} {1} is bidding...".format(self.name, self.pNum))
                
                try:
                    bid = random.randint(self.gs['high_bid']+1,5)
                except ValueError: # Because randint(6,5) fails.
                    bid = 5
                log.info("{0} {1} considers bidding {2}...".format(
                        self.name, self.pNum, bid))
                r = random.random()
                if self.is_legal_bid(bid) and (r < 0.6):
                    self.bid(bid)
                    log.info("{0} {1} bids {2}".format(
                            self.name, self.pNum, bid))
                else:
                    self.bid(0)
                    log.info("{0} {1} passes.".format(self.name, self.pNum))
