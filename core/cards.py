#!/usr/bin/python3
"""
Define basic properties of cards and decks of cards. 
"""
import random
from os import name as os_name
from math import floor


# Constants to use for card identification -- copying style from VB
cdCLUBS = 0;        cdDIAMONDS = 1;         cdHEARTS = 2;       cdSPADES = 3
cdTWO = 2;          cdTHREE = 3;            cdFOUR = 4;         cdFIVE = 5
cdSIX = 6;          cdSEVEN = 7;            cdEIGHT = 8;        cdNINE= 9
cdTEN = 10;         cdJACK = 11;            cdQUEEN = 12;       cdKING = 13
cdACE = 14

# Provide two-way lookup for ranks and suits by name and number.
RANKS_BY_NUM = {cdTWO:'Two',        cdTHREE:'Three',    cdFOUR:'Four',  
                cdFIVE:'Five',      cdSIX:'Six',        cdSEVEN:'Seven',
                cdEIGHT:'Eight',    cdNINE:'Nine',      cdTEN:'Ten', 
                cdJACK:'Jack',      cdQUEEN:'Queen',    cdKING:'King',     
                cdACE:'Ace'}

RANKS_SHORT = {cdTWO:'2',   cdTHREE:'3',    cdFOUR:'4',     cdFIVE:'5', 
               cdSIX:'6',   cdSEVEN:'7',    cdEIGHT:'8',    cdNINE:'9',
               cdTEN:'T',   cdJACK:'J',     cdQUEEN:'Q',    cdKING:'K',
               cdACE:'A'}

SUITS_BY_NUM = {cdCLUBS:'Clubs', cdDIAMONDS:'Diamonds', cdHEARTS:'Hearts', 
                cdSPADES:'Spades'}

# Code to support deprecated/legacy development platforms:
if os_name == 'nt':
    SUITS_SHORT = {0:'C', 1:'D', 2:'H', 3:'S'}
else: # Unicode is awesome
    SUITS_SHORT = {0:'\u2663', 1:'\u2666', 2:'\u2665', 3:'\u2660'}

NUM_RANKS = 13
NUM_SUITS = 4


class Card:
    """
    Define Card object with instance variables:

    suit (int): card suit via Suits enum
    rank (int): card rank via Ranks enum
    code (int): rank-suit encoding of card; only set when card dealt      
    owner (int, 0-3): local player id for initial holder of card
        - currently set in game.py when dealt
    """
    def __init__(self, rank_or_code, suit=None):
        """Create Card object with given rank & suit."""
        if suit is None: # Assume it's a 1-52 encoded card.
            self.suit = (rank_or_code-1)//NUM_RANKS
            self.rank = rank_or_code - self.suit*NUM_RANKS + 1
        else:
            self.rank = rank_or_code
            self.suit = suit
        self.code = self.encode()
        self.owner = None
        
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
        return c


def decode(card_code):
    """Decode card encoding into (rank, suit) pair."""
    suit = floor((card_code - 1) / NUM_RANKS)
    rank = card_code - (suit * NUM_RANKS) + 1
    
    return rank, suit
