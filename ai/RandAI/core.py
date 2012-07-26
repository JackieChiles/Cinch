#!/usr/bin/python3
"""Rand: The pesudo-random master."""

import random

# Import base class for AI agent
from ai.base import AIBase


class Rand(AIBase):
    def __init__(self):
        super().__init__()   # pref. way of calling parent init

        print("RandAI loaded")

    def act(self):
        """Overriding base class act."""
        
        name = self.identity['name']
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                print(name, self.pNum, "is playing...")
                legal_cards = []
                for c in self.hand:
                    if self.is_legal_play(c):
                        legal_cards.append(c)
                chosen_card = random.randint(0,len(legal_cards)-1)
                self.play(legal_cards[chosen_card])
                print(name, self.pNum, "plays",
                      self.print_card(legal_cards[chosen_card]))

            elif self.gs['mode'] == 2: # Bid
                print(name, self.pNum, "is bidding...")
                r = random.random()
                if self.is_legal_bid(self.gs['high_bid']+1) and (r < 0.5):
                    self.bid(self.gs['high_bid']+1)
                    print(name, self.pNum, "bids", bid)
                else:
                    self.bid(0)
                    print(name, self.pNum, "passes.")
