#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""

import random

# Import base class for AI agent -- may need to edit import path
try:
    from ....base import AIBase
except:
    from base import AIBase


class RandomAgent(AIBase):
    def __init__(self):
        super().__init__()   # pref. way of calling parent init

        print("RandomAgent AI loaded")

    def act(self):
        """Overriding base class act."""
        
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                print("pNum", self.pNum, "Thinking about play...")
                #Play first legal card
                for c in self.hand:
                    if self.is_legal_play(c):
                        self.play(c)
                        print("pNum", self.pNum, "Playing", c)
                        break

            elif self.gs['mode'] == 2: # Bid
                print("pNum", self.pNum, "Thinking about bid...")
                
                bid = random.randint(1,4)  # Will never bid cinch
                r = random.random()
                if ((bid > self.gs['high_bid']) and (r < 0.75)):
                    self.bid(bid)
                    print("pNum", self.pNum, "Bidding", self.gs['high_bid']+1)
                else:
                    self.bid(0)
                    print("pNum", self.pNum, "Passing bid")
