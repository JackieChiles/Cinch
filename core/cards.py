#!/usr/bin/python3
"""
Provide facilities for Deck and Card objects for Cinch card game, which
will include Cinch-specific properties as needed. It is undesirable to
delegate all Cinch-specific properties to higher level objects for this
implementation.
"""
import random
import os


# Provide two-way lookup for ranks and suits by name and number.
RANKS_BY_NUM = {2:'two', 3:'three', 4:'four', 5:'five', 6:'six', 7:'seven',
                8:'eight', 9:'nine', 10:'ten', 11:'jack', 12:'queen',
                13:'king', 14:'ace'}
RANKS_BY_NAME = {v:k for k, v in RANKS_BY_NUM.items()}
RANKS_SHORT = {2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9',
               10:'T', 11:'J', 12:'Q', 13:'K', 14:'A'}
SUITS_BY_NUM = {0:'clubs', 1:'diamonds', 2:'hearts', 3:'spades'}
SUITS_BY_NAME = {v:k for k, v in SUITS_BY_NUM.items()}

NUM_RANKS = 13
NUM_SUITS = 4

# Code to support deprecated/legacy development platforms:
if os.name == 'nt':
    SUITS_SHORT = {0:'C', 1:'D', 2:'H', 3:'S'}
else:
    SUITS_SHORT = {0:'\u2663', 1:'\u2666', 2:'\u2665', 3:'\u2660'}


class Card:
    """
    Define Card object with instance variables:

    suit (int): card suit via Suits enum
    rank (int): card rank via Ranks enum
    code (int): rank-suit encoding of card; only set when card dealt
    legal_play (boolean): Is this card a legal play for current game state?
        ##is legal_play needed?
        
    owner (int, 0-3): local player id for initial holder of card
    taker (int, 0-3): local player id for player that took trick with this
    """
    def __init__(self, rank, suit):
        """Create Card object with given rank & suit."""
        self.rank = rank
        self.suit = suit
        
    def __lt__(self, other):
        """Implemented to make class sortable."""
        return ((self.suit == other.suit and self.rank < other.rank) or
                (self.suit is not 2 and other.suit is 2) or
                (self.suit is not 2 and other.suit is not 2 and self.suit <
                other.suit))
                
    def __eq__(self, other):
        """Implemented to make class sortable."""
        return self.suit == other.suit and self.rank == other.rank

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "{r}{s}".format(r=RANKS_SHORT[self.rank],
                                   s=SUITS_SHORT[self.suit])
        
    def encode(self):
        """Encode (rank, suit) into integer in range 1-52."""
        return (self.rank-1) + (self.suit*NUM_RANKS)


class Deck(list):
    """
    Define Deck object (extending list built-in) and class methods for
    creating and manipulating Deck.
    """
    def __init__(self):
        """
        Create deck of cards. Iterate through (rank,suit) pairs, creating
        a new Card object for each and adding to internal list.
        """
        for r in RANKS_BY_NUM:
            for s in SUITS_BY_NUM:
                self.append(Card(r, s))

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Deck of cards containing {0} cards.".format(len(self))
    
    def deal_one(self):
        """
        Return random card from deck and remove from self.
        Avoids need for separate 'shuffle' method.
        """
        c = self.pop(random.randint(0, len(self)-1))
        c.code = c.encode()
        return c


SUIT_TERMS = [NUM_RANKS*x for x in range(NUM_SUITS)]
def decode(card_code):
    """Decode card encoding into (rank, suit) pair."""
    val = card_code+1
    for term in SUIT_TERMS:
        if val - term in RANKS_BY_NUM:
            return (val-term, int(term/NUM_RANKS))

    return 0, 0

