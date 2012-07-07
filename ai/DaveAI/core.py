#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""

import random

# Import base class for AI agent -- may need to edit import path
from base import AIBase


class Dave(AIBase):
    def __init__(self):
        super().__init__()   # pref. way of calling parent init

        print("DaveAI loaded")

    def act(self):
        """Overriding base class act."""
        
        name = self.identity['name']
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                print(name, self.pNum, "is playing...")
                #Play first legal card
                for c in self.hand:
                    if self.is_legal_play(c):
                        self.play(c)
                        print(name, self.pNum, "plays", self.print_card(c))
                        break

            elif self.gs['mode'] == 2: # Bid
                print(name, self.pNum, "is bidding...")
                
                if self.gs['high_bid'] < 4:
                    bid = random.randint(self.gs['high_bid']+1,4) # Never cinch
                else:
                    bid = 0
                print(name, self.pNum, "considers bidding", bid)
                r = random.random()
                if ((bid > 0) and (r < 0.75)):
                    self.bid(bid)
                    print(name, self.pNum, "bids", bid)
                else:
                    self.bid(0)
                    print(name, self.pNum, "passes.")
