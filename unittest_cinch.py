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


if __name__ == "__main__":
    unittest.main()