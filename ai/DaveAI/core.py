#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""

import random

# Import base class for AI agent -- may need to edit import path
from ai.base import AIBase, log


class Dave(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

    def act(self):
        """Overriding base class act."""
        if self.pNum==self.gs['active_player']:
            if self.gs['mode'] == 1: # Play
                log.info("{0} is playing...".format(self.label))
                #Play first legal card
                for c in self.hand:
                    if self.is_legal_play(c):
                        self.play(c)
                        break

            elif self.gs['mode'] == 2: # Bid
                log.info("{0} is bidding...".format(self.label))
                
                if self.gs['high_bid'] < 4:
                    bid = random.randint(self.gs['high_bid']+1,4) # Never cinch
                else:
                    bid = 0
                log.info("{0} considers bidding {1}...".format(self.label, bid))

                r = random.random()
                if ((bid > 0) and (r < 0.75)):
                    self.bid(bid)
                else:
                    self.bid(0)
    
    def handle_response(self, response):
        """Overriding base class handle_response. This is to demonstrate how
        to hijack the normal response handler to do custom stuff without
        copying the entire function.
        
        response (dict): message from Comet server
        
        """
        for msg in response['msgs']:
            if 'addC' in msg: # Start of hand
                self.chat("Good luck everyone. You'll need it.")

        super().handle_response(response) # Return message to default handler    
    
