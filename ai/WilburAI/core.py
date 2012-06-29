#!/usr/bin/python3
"""Wilbur: everyone's favorite hapless cinching AI."""

import random

# Import base class for AI agent -- may need to edit import path
try:
    from ....base import AIBase
except:
    from base import AIBase


class Wilbur(AIBase):
    def __init__(self):
        super().__init__()   # pref. way of calling parent init

        print("WilburAgent AI loaded")

    def act(self):
        """Overriding base class act."""
        
        name = self.identify_self()['name']
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                print(name, self.pNum, "is playing...")
                for c in reversed(self.hand):
                    if self.is_legal_play(c):
                        self.play(c)
                        print(name, self.pNum, "plays", c)
                        break

            elif self.gs['mode'] == 2: # Bid
                print(name, self.pNum, "is bidding...")
                
                try:
                    bid = random.randint(self.gs['high_bid']+1,5)
                except ValueError: # Because randint(6,5) fails.
                    bid = 5
                print(name, self.pNum, "considers bidding", bid)
                r = random.random()
                if self.is_legal_bid(bid) and (r < 0.6):
                    self.bid(bid)
                    print(name, self.pNum, "bids", bid)
                else:
                    self.bid(0)
                    print(name, self.pNum, "passes.")
