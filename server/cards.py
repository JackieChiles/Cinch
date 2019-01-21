# -*- coding: utf-8 -*-
"""Define basic properties of cards and decks of cards."""

from random import shuffle
from math import floor


# Constants to use for card identification
RANKS_MAP = {2: ('2', 'Two'),    3: ('3', 'Three'),   4: ('4', 'Four'),
             5: ('5', 'Five'),   6: ('6', 'Six'),     7: ('7', 'Seven'),
             8: ('8', 'Eight'),  9: ('9', 'Nine'),    10: ('T', 'Ten'),
             11: ('J', 'Jack'),  12: ('Q', 'Queen'),  13: ('K', 'King'),
             14: ('A', 'Ace')}
RANKS = RANKS_MAP.keys()

SUITS_MAP = {0: ('♣', 'Clubs'),         # club symbol:    '\u2663'
             1: ('♦', 'Diamonds'),      # diamond symbol: '\u2666'
             2: ('♥', 'Hearts'),        # heart symbol:   '\u2665'
             3: ('♠', 'Spades')}        # spade symbol:   '\u2660'
SUITS = SUITS_MAP.keys()

# Lookup tables for conversion, filled below
CODE_TO_RS = {}
RS_TO_CODE = {}

NUM_RANKS = len(RANKS)
NUM_SUITS = len(SUITS)
MAX_CARD_CODE = NUM_RANKS * NUM_SUITS

# Control variables locked in at program start
STACK_DECK = False
DECK_SEED  = 0 # Used for deck stacking, must be in interval [0, 1]


# Define exceptions
class OutOfRangeError(Exception): pass
class InvalidRankError(Exception): pass
class InvalidSuitError(Exception): pass


class Card:
    """Define Card object with instance variables:

    suit (int): card suit via Suits enum
    rank (int): card rank via Ranks enum
    code (int): rank-suit encoding of card; only set when card dealt
    owner (int, 0-3): local player id for initial holder of card
        - currently set in game.py when dealt

    """
    def __init__(self, rank_or_code, suit=None):
        """Create Card object with given rank & suit."""
        if suit is None: # Assume it's a 1-52 encoded card.
            self.code = rank_or_code
            self.rank, self.suit = decode(rank_or_code)
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
        return "{r}{s}".format(r=RANKS_MAP[self.rank][0],
                                   s=SUITS_MAP[self.suit][0])

    def encode(self):
        """Convenience method for calling encode."""
        return encode(self.rank, self.suit)


class Deck(list):
    """Define Deck object and methods for creating and manipulating Deck."""
    def __init__(self):
        """Create deck of cards.

        Iterate through (rank,suit) pairs, creating a new Card object
        for each and adding to internal list.

        """
        for r in RANKS:
            for s in SUITS:
                self.append(Card(r, s))

        # Shuffle deck, stacking if needed
        if STACK_DECK:
            shuffle(self, lambda: DECK_SEED)
        else:
            shuffle(self)

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Deck of Cards containing {0} cards.".format(len(self))

    def deal_one(self):
        """Return top from deck and remove from self."""
        return self.pop(0)


def encode(rank, suit):
    """Encode (rank, suit) into integer in range 1-52."""
    if rank not in RANKS:
        raise InvalidRankError("Invalid rank: %s" % rank)
    if suit not in SUITS:
        raise InvalidSuitError("Invalid suit: %s" % suit)

    return RS_TO_CODE[(rank, suit)]

def decode(card_code):
    """Decode card encoding into (rank, suit) pair."""
    if not (0 < card_code < MAX_CARD_CODE+1):
        raise OutOfRangeError("Invalid card code: %s" % card_code)

    return CODE_TO_RS[card_code]

def fillLookupTables():
    """Store all possible (code, (rank, suit)) pairs and the reverse."""
    for code in range(1, MAX_CARD_CODE+1):
        suit = floor((code - 1) / NUM_RANKS)
        rank = code - (suit * NUM_RANKS) + 1

        CODE_TO_RS[code] = (rank, suit)
        RS_TO_CODE[(rank, suit)] = code

fillLookupTables()
