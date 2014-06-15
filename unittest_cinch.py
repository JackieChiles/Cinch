#!/usr/bin/python2
# -*- coding: utf-8 -*-

"""Unit test for Cinch"""

import unittest

"""Tests for card encoding"""

from core import cards
MAX_CARD_CODE = 52

card_codes = range(1, MAX_CARD_CODE+1)


class GoodInput(unittest.TestCase):
    def testDecode(self):
        """decode should produce valid ranks and suits"""
        for integer in card_codes:
            r, s = cards.decode(integer)
            self.assertIn(r, cards.RANKS_SHORT)
            self.assertIn(s, cards.SUITS_SHORT)
            
    def testEncode(self):
        """encode should produce valid card codes"""
        for r in cards.RANKS_SHORT:
            for s in cards.SUITS_SHORT:
                c = cards.Card(r, s)
                self.assertIn(c.code, card_codes)

class BadInput(unittest.TestCase):
    def testBadCardCode(self):
        """decode should fail with out of range input"""
        for code in (0, -3, 53, 100):
            self.assertRaises(cards.OutOfRangeError, card.decode, code)
        
    def testBadRankSuit(self):
        """encode should fail with invalid input"""
        c = cards.Card(1)
        for r in ('c', '22', 'y', '0'):
            c.rank = r
            self.assertRaises(cards.InvalidRank, card.encode)
        
        c.rank = '3' # Reset to valid rank
        for s in ('z', '3', 'a', '0'):
            c.suit = s
            self.assertRaises(cards.InvalidSuit, card.encode)
    
class SanityCheck(unittest.TestCase):
    def testSanity(self):
        """encode(decode(n))==n for all n"""
        c = cards.Card(1) # Initialize Card object
        
        for integer in card_codes:
            c.rank, c.suit = cards.decode(integer)
            self.assertEqual(integer, c.encode())


if __name__ == "__main__":
    unittest.main()