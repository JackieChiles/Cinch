#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""

import random
from collections import defaultdict

# Import base class for AI agent
import core.cards as cards
from ai.base import AIBase, MyCard, log
from core.gamestate import NUM_PLAYERS


NUM_MC_TRIALS = 30 # Number of Monte Carlo trials to run for play analysis
TAKE_TRICK_PROB_THRESHOLD = 0.5 # How confident AI must be to play for the trick
UNCERTAINTY_MULTS = [1, 0.8, 0.75, 0.66] # index=num_to_add

FACE_CARDS = [cards.ACE, cards.KING, cards.QUEEN, cards.JACK]
GAME_POINT_VALUES = {cards.TEN:10, cards.ACE:4, cards.KING: 3,
                     cards.QUEEN: 2, cards.JACK:1}

class Hal(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

        self.target_suit = None # If agent wins bid, set this as trump
        self.hand_by_suit = None
        
        self.game_started = False
        
        self.wincount = 0 #used for tracking stuff while debugging
        self.trickcount = 0
        
    def act(self):
        """Overriding base class act."""
        
        # Update card zones for card counting purposes

        if self.pNum==self.gs['active_player']:
            label = "{0}/{1}".format(self.name, self.pNum) # Cleans up logging

            #====================
            # Play logic
            #====================
            if self.gs['mode'] == 1: # Play
                log.info("{0} is playing...".format(label))
                
                legal_plays = self.get_legal_plays(True)
                
                # Perform play analysis -- filter out illegal plays now
                play = self.think_on_play(legal_plays) # Returns MyCard
                play = play.val
                
                # Make final play determination
                if self.is_legal_play(play):
                    self.play(play)
                else:
                    #Make a legal play
                    log.error("Agent decided on illegal play ({0}); "
                              "forcing legal play".format(play.val))
                    
                    #Play first legal card
                    self.play(legal_plays[0].val)

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
                    
                r = random.random()
                if (r < .50) and (bid > 0): # Half the time bid conservatively
                    bid -= 1

                # Make final bid determination

                # Check if stuck as dealer
                #  (agent wants to pass as dealer & all other folks pass)
                if ((self.gs['dealer'] == self.pNum) and  
                        (self.gs['high_bid'] == 0) and
                        (bid == 0)):
                    log.info("{0} is stuck as dealer".format(label))
                    bid = 1 # Make minimum legal bid
                else:
                    if bid <= self.gs['high_bid']:
                        bid = 0 # Pass

                # Transmit bid
                if self.is_legal_bid(bid):
                    self.bid(bid)
                else:
                    log.error("Agent failed to make legal bid of {0}".format(
                            bid))
                    self.bid(0) # Try passing

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
            
            if 'playC' in msg: # Must be czeched before addC and remP !!
                if msg['actor'] == self.pNum:
                    source = self.hand_zone # Move card from hand_zone to play
                else:
                    source = self.unseen_zone # Move card from unseen to play
                
                card = self.get_card_by_code(msg['playC'], source)
                self.move_card(card, source, self.play_zone)
            
            if 'addC' in msg:
                # Update card zones for new hand for card counting
                self.reset_card_zones()
                new_cards = msg['addC'] # List of encoded cards
                for val in new_cards:
                    card = self.get_card_by_code(val, self.unseen_zone)
                    self.move_card(card, self.unseen_zone, self.hand_zone)
 
            if 'remP' in msg:
                self.trickcount += 1
                if msg['remP'] == self.pNum:
                    self.wincount += 1

                for card in list(self.play_zone):
                    self.move_card(card, self.play_zone, self.seen_zone)
                
            if 'win' in msg:
                self.log("WIN RATIO: {0} / {1} = {2}".format(self.wincount, self.trickcount, self.wincount/self.trickcount))

                
            # add 'amusing' responses from
            # http://www.imdb.com/title/tt0062622/quotes etc

        super().handle_response(response) # Return message to default handler    

    def get_card_by_code(self, needle, haystack):
        """Search through list to find MyCard object based on encoding.
        
        needle (int): card encoding
        haystack (list): list to search
        
        """
        for item in haystack:
            if needle == item.val:
                return item

        return None
        
    def reset_card_zones(self):
        """Reset card zones for new hand."""
        # Card object zones
        self.unseen_zone = self.init_unseen_zone()
        self.hand_zone = [] # Not the same as self.hand, a list of encoded cards
        self.play_zone = []
        self.seen_zone = [] # May end up not caring about this at all
            
    def think_on_bid(self):
        """Evaluate hand and return proposed bid.
        
        returns 0, 1, 2, or 3.
        
        """
        self.fancify_hand() # Decode and store hand for easier manip

        suit_points = defaultdict(int)
        
        for suit in self.hand_by_suit:
            this_suit = [x.rank for x in self.hand_by_suit[suit]]

            # If high card in suit is A, K, or Q, add a point to this suit
            if max(this_suit) in [cards.QUEEN, cards.KING, cards.ACE]:
                suit_points[suit] += 1
                
            # If low card in suit is 2, 3, or 4, add a point to this suit
            if min(this_suit) in [cards.TWO, cards.THREE, cards.FOUR]:
                suit_points[suit] += 1
                
            # If jack of suit is present, add a point to this suit
            if cards.JACK in this_suit: # Jack = 11
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
            
        self.target_suit = big_suit  # TODO: Use this if we win bid
        return max_points
    
    def think_on_play(self, legal_plays):
        """Perform play analysis.
        
        legal_plays (list): list of MyCards that are deemed legal plays
        
        """
        probs = defaultdict(list) # key=probability, value=list of cards
        
        play_zone = self.play_zone
        num_in_play = len(play_zone)
        
        get_winning_card = self.get_winning_card #speed++
        
        if len(legal_plays) == 1: # Trivial case, but it happens
            return legal_plays[0]
        
        num_to_add = NUM_PLAYERS - len(play_zone) - 1 # #cards to add after play
        uncertainty_factor = UNCERTAINTY_MULTS[num_to_add]
        
        # For each card in legal_plays, determine likelihood of it winning trick
        # Consider number of cards in play and unseen cards. And that's it.
        for card in legal_plays:
            # Play card in virtual zone
            virtual_play_zone = list(play_zone)
            virtual_play_zone.append(card)
            card_led = virtual_play_zone[0]

            # Fill up as needed (until len == NUM_PLAYERS)
            if len(virtual_play_zone) == NUM_PLAYERS:
                # Virtual play completes trick; determine if card wins it
                # p_card = probability of winning trick with card
                p_card = 1 * (card == get_winning_card(virtual_play_zone, 
                                                       card_led))
                
            else:
                # Fill up virtual play zone with random selections from unseen
                # cards (Monte Carlo trials). Do this X times and determine
                # proportion of times card wins.
                tot = 0 # Number of trials conducted
                wins = 0 # Number of trials card wins
                
                for i in range(NUM_MC_TRIALS):
                    tmp_play_zone = list(virtual_play_zone)
                    
                    # Select num_to_add at random from unseen_zone & play
                    ###this could result in illegal plays by !agents. TODO
                    selection = random.sample(self.unseen_zone, num_to_add)
                    tmp_play_zone.extend(selection)
                    
                    if card == get_winning_card(tmp_play_zone, card_led):
                        wins += 1
                    
                p_card = wins / NUM_MC_TRIALS * uncertainty_factor
                
            probs[p_card].append(card)
        
        max_prob = max(probs)
        candidates = probs[max_prob]
        
        if max_prob == 1:
            # Play the weakest winning card, since win is guaranteed
            if len(candidates) > 1:
                material_values = self.get_material_values(candidates)
                return material_values[min(material_values)][0]
            else:
                return candidates[0]
        
        elif max_prob >= TAKE_TRICK_PROB_THRESHOLD:   # Consider threshold
            if len(candidates) > 1: # Multiple cards have max_prob of win
                # If multiple cards have equal probabilities of win, maybe treat
                # them differently?           #TODO
                return candidates[0]
                
            else:  # Only one card has the max_prob of win
                return candidates[0]
                
        else: # No play meets the threshold, so adopt Protect Material strategy
            # Assign a value to each legal play based on worth (eg. game points)
            material_values = self.get_material_values(legal_plays)
            
            # Select a card with the lowest material value to play
            return material_values[min(material_values)][0]              
    
    def get_material_values(self, cards):
        """Make list of material values for cards.
        
        cards (list of MyCards): cards to evaluate
        
        """
        vals = defaultdict(list)
        
        for card in cards:
            v = card.rank
            if card.rank in GAME_POINT_VALUES:
                v += GAME_POINT_VALUES[card.rank]
            
            vals[v].append(card)
        
        return vals
        
    def fancify_hand(self):
        """Decode and store hand for easier manipulation."""
        hand_by_suit = defaultdict(list) # Only useful for bidding
        for card in self.hand_zone:
            hand_by_suit[card.suit].append(card)
        
        self.hand_by_suit = hand_by_suit

    def init_unseen_zone(self):
        """Return list of MyCard objects representing full deck."""
        zone = []
        
        for r in cards.RANKS_BY_NUM:
            for s in cards.SUITS_BY_NUM:
                zone.append(MyCard(self.encode_card(r,s), r, s))
        
        return zone
        
    def move_card(self, target, source, dest):
        """Move target from source to dest.
        
        target (MyCard object): card to move
        source (list): list to move target from
        dest (list): list to move target to
        
        """
        if target is None:
            log.error("Cannot move card 'None'!")
        source.remove(target)
        dest.append(target)
        
