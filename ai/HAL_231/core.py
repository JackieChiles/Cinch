#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""

import random
from collections import defaultdict

# Import base class for AI agent
from core.cards import * # Not best practices, but it makes life good here
from ai.base import AIBase, log


class Hal(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

        log.info("{0}AI loaded".format(self.name))
        
        self.target_suit = None # If agent wins bid, set this as trump
        self.fancy_cards = None
        self.hand_by_suit = None
        
        self.game_started = False

    def act(self):
        """Overriding base class act."""
        label = "{0}/{1}".format(self.name, self.pNum) # Clean up logging lines
        
        if self.pNum==self.gs['active_player']:

            #====================
            # Play logic
            #====================
            if self.gs['mode'] == 1: # Play
                log.info("{0} is playing...".format(label))
                #Play first legal card
                for c in self.hand:
                    if self.is_legal_play(c):
                        self.play(c)
                        log.info("{0} plays {1}".format(
                                    label, self.print_card(c)))
                        break

            #====================
            # Bid logic
            #====================
            elif self.gs['mode'] == 2: # Bid
                log.info("{0} is bidding...".format(label))
                
                # Evaluate hand for bidding strength
                bid = self.think_on_bid() # Has max return value of 3

                # Add some element of chance (i.e. risk/luck/error)
                r = random.random()
                if r < .20:  # 20% of time Agent would bid 1 more
                    bid += 1
                elif r < .02: # 2% of time Agent would bid 2 more
                    bid += 2

                # Transmit bid                            
                if bid > self.gs['high_bid']:
                    self.bid(bid)
                    log.info("{0} bids {1}".format(label, bid))
                else:
                    # Check if stuck dealer (dealer wants to pass on high of 0)
                    if ((self.gs['dealer'] == self.pNum) and 
                            (self.gs['high_bid'] == 0)):
                       self.bid(1) # Make minimum legal bid
                       log.info("{0} is dealer-stuck, bids {1}."
                                "".format(label, bid))

                    else:
                        self.bid(0) # Bid isn't legal or bid is 0, so pass
                        log.info("{0} passes.".format(label))
    
    def think_on_bid(self):
        """Evaluate hand and return proposed bid.
        
        returns 0, 1, 2, or 3.
        
        """
        self.fancify_hand() # Decode and store hand for easier manip

        suit_points = defaultdict(int)
        
        for suit in self.hand_by_suit:
            this_suit = [x.rank for x in self.hand_by_suit[suit]]

            # If high card in suit is A, K, or Q, add a point to this suit
            if max(this_suit) in [cdQUEEN, cdKING, cdACE]:
                suit_points[suit] += 1
                
            # If low card in suit is 2, 3, or 4, add a point to this suit
            if min(this_suit) in [cdTWO, cdTHREE, cdFOUR]:
                suit_points[suit] += 1
                
            # If jack of suit is present, add a point to this suit
            if cdJACK in this_suit: # Jack = 11
                suit_points[suit] += 1
        
        # Select max of suit_points; if tied, pick suit with most cards
        try:
            max_points = max(suit_points.values())
        except ValueError: # suit_points is empty
            return 0

        if list(suit_points.values()).count(max) > 1: # A tie exists
            big_suit = -1
            suit_size = -1
            for suit in suit_points: # Search for suits with max_points
                if suit_points[suit] == max_points:
                    if len(self.hand_by_suit[suit]) > suit_size: # Find
                        suit_size = len(self.hand_by_suit[suit]) # biggest
                        big_suit = suit                          # suit

        else:
            for suit in suit_points:
                if suit_points[suit] == max_points:
                    big_suit = suit
                    break
            
        self.target_suit = big_suit  # Use this if we win bid
        return max_points
    
    def fancify_hand(self):
        """Deocde and store hand for easier manipulation."""
        fancy_cards = []
        hand_by_suit = defaultdict(list)
        for card in self.hand:
            r, s = self.decode_card(card)
            cur = MyCard(card, r, s)
            fancy_cards.append(cur)
            
            hand_by_suit[s].append(cur)
        
        self.fancy_cards = fancy_cards        
        self.hand_by_suit = hand_by_suit
        
    def handle_response(self, response):
        """Overriding base class handle_response. This is to demonstrate how
        to hijack the normal response handler to do custom stuff without
        copying the entire function.
        
        response (dict): message from Comet server
        
        """
        for msg in response['msgs']:
            if ('addC' in msg) and not self.game_started: # Start of hand
                self.chat("Daisy, Daisy, give me your answer do.")
                self.game_started = True
                
            # add 'amusing' responses from
            # http://www.imdb.com/title/tt0062622/quotes etc

        super().handle_response(response) # Return message to default handler    


class MyCard:
    # Helper class for organizing cards
    def __init__(self, val, rank, suit):
        self.val = val
        self.rank = rank
        self.suit = suit
        
    def __repr__(self):
        return "{0}/{1}-{2}".format(self.val, self.rank, self.suit)
