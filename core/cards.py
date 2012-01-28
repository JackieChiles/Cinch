#!/usr/bin/python3
"""
Provide facilities for Deck and Card objects for Cinch card game, which
will include Cinch-specific properties as needed. It is undesirable to
delegate all Cinch-specific properties to higher level objects for this
implementation.
"""
import random


##Provide two-way lookup for ranks and suits by name and number.
##Placed outside Card class to avoid wasted memory
##(don't need 52 copies of these dictionaries).
RANKS_BY_NUM = {2:'two', 3:'three', 4:'four', 5:'five', 6:'six', 7:'seven',
                8:'eight', 9:'nine', 10:'ten', 11:'jack', 12:'queen',
                13:'king', 14:'ace'}
RANKS_BY_NAME = {v:k for k, v in RANKS_BY_NUM.items()}
RANKS_SHORT = {2:'2', 3:'3', 4:'4', 5:'5', 6:'6', 7:'7', 8:'8', 9:'9',
               10:'T', 11:'J', 12:'Q', 13:'K', 14:'A'}
SUITS_BY_NUM = {0:'clubs', 1:'diamonds', 2:'hearts', 3:'spades'}
SUITS_BY_NAME = {v:k for k, v in SUITS_BY_NUM.items()}
SUITS_SHORT = {0:'C', 1:'D', 2:'H', 3:'S'}


class Card:
    """
    Define Card object with instance variables:

    suit (int): card suit via Suits enum
    rank (int): card rank via Ranks enum
    legal_play (boolean): Is this card a legal play for current game state?
    owner (int, 0-3): local player id for initial holder of card
    taker (int, 0-3): local player id for player that took trick with this
    """
    def __init__(self, rank, suit):
        """Create Card object with given rank & suit."""
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "{r}{s}".format(r=RANKS_SHORT[self.rank],
                                   s=SUITS_SHORT[self.suit])
        
    def encode(self):
        """Encode (rank, suit) into integer in range 1-52."""
        return (self.rank-1) + (self.suit*len(RANKS_BY_NUM))


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
        return self.pop(random.randint(0, len(self)-1))
        
        
##tests
if __name__ == '__main__':    
    d = Deck()
    for c in d:
        print(RANKS_BY_NUM[c.rank], SUITS_BY_NUM[c.suit])
    c = d.deal_one()
    print(c, c.encode())
