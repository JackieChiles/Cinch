#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""
import random

from ai.base import AIBase, log


# AI Agent description -- used by Manager for identification
AI_CLASS = "Dave" # Set this to match the class name for the agent
__author__  = "M.G."
__version__ = "1.2"
__date__    = "19 September 2012"
__skill__   = "0"
__agent_name__  = "Dave"
__description__ = "Leads from the left."


class Dave(AIBase):
    identity = {  'author':   __author__,
                  'version':  __version__,
                  'date':     __date__,
                  'skill':    __skill__,
                  'name':     __agent_name__,
                  'description':  __description__
                 }
                 
    def __init__(self, pipe):
        super().__init__(pipe, identity)  # Call to parent init

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
    
