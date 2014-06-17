#!/usr/bin/python2
# -*- coding: utf-8 -*-

"""Unit test for Cinch"""

import unittest

"""Tests for card encoding"""

from core import cards

MAX_CARD_CODE = 52
card_codes = range(1, MAX_CARD_CODE+1)
RANKS = range(2, 15)
SUITS = range(0, 4)

class GoodInput(unittest.TestCase):
    knownValues = ((1, 2, 0),
                   (52, 14, 3),
                   (21, 9, 1),
                   (36, 11, 2))

    def testDecodeKnowns(self):
        """decode should give known result with known input"""
        for code, rank, suit in self.knownValues:
            r, s = cards.decode(code)
            self.assertEqual(rank, r)
            self.assertEqual(suit, s)
            
    def testEncodeKnowns(self):
        """encode should give known result with known input"""
        for code, rank, suit in self.knownValues:
            c = cards.Card(rank, suit).encode()
            self.assertEqual(code, c)
    
    def testDecodeValidity(self):
        """decode should produce valid ranks and suits"""
        for integer in card_codes:
            r, s = cards.decode(integer)
            self.assertIn(r, RANKS)
            self.assertIn(s, SUITS)
            
    def testEncodeValidity(self):
        """encode should produce valid card codes"""
        for r in RANKS:
            for s in SUITS:
                c = cards.Card(r, s)
                self.assertIn(c.code, card_codes)

class BadInput(unittest.TestCase):
    def testBadCardCode(self):
        """decode should fail with out of range input"""
        for code in (0, -3, 53, 100):
            self.assertRaises(cards.OutOfRangeError, cards.decode, code)
        
    def testBadRankSuit(self):
        """encode should fail with invalid input"""
        c = cards.Card(1)
        for r in (-1, 0, 1, 15, 20):
            c.rank = r
            self.assertRaises(cards.InvalidRankError, c.encode)
        
        c.rank = 2 # Reset to valid rank
        for s in (-1, 4):
            c.suit = s
            self.assertRaises(cards.InvalidSuitError, c.encode)
    
class SanityCheck(unittest.TestCase):
    def testSanity(self):
        """encode(decode(n))==n for all n"""
        c = cards.Card(1) # Initialize Card object
        
        for integer in card_codes:
            c.rank, c.suit = cards.decode(integer)
            self.assertEqual(integer, c.encode())

class AITests(unittest.TestCase):
    def __init__(self, p):
        unittest.TestCase.__init__(self, p)
        
        # Initialize an empty, unstarted AI object
        from ai import base
        self.ai = base.AIBase.__new__(base.AIBase)
        
        # Configure the AI for testing
        self.ai.gs = base.GS()
        self.ai.hand = list()
        self.ai.resetGamestate()
        self.pNum = None
    
    def testPlayLegality(self):
        """ai base should properly evaluate play legality"""
        # Configure a sample gamestate
        from core.cards import Card
        
        func = self.ai.is_legal_play # Focus of this test
        
        # Starting hand for AI
        self.ai.hand = [Card(2), Card(15)] # 3C, 3D
        
        # Ensure it is legal to play anything on an empty board
        self.ai.gs.cardsInPlay = [] # Clear board
        self.assertTrue(func(Card(1)))
        
        # Ensure it is legal to play trump
        self.ai.gs.trump = 0 # Clubs
        self.ai.gs.cardsInPlay = [Card(1)] # 2 Clubs        
        self.assertTrue(func(Card(2))) # 3 Clubs
        
        # Ensure it is legal to follow suit (that isn't trump)
        # 2D is led, we play 3D
        self.ai.gs.cardsInPlay = [Card(14)] # 2D
        self.assertTrue(func(Card(15))) # 3D
        
        # Ensure it is illegal to choose not to follow suit
        # 2D was led, we play 3H (not in hand) but 3D (in hand) is legal
        self.assertFalse(func(Card(28))) # 3H, could've played 3D
        
        # Ensure it is legal to throw off
        # 2D was led, we only have AS
        self.ai.hand = [Card(52)] # AS
        self.assertTrue(func(Card(52)))
        

if __name__ == "__main__":
    unittest.main()