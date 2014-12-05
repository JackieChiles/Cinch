#!/usr/bin/python2
"""Goofus: AI agent that uses heuristics based only on the current game state.

Goofus does not use historical information as of v1.0.

A flexible system for play decisions allows generic rules to be added, removed,
or reordered fairly easily. See the play method for the current setup of play
heuristic rules.

Version 1.0 rules can also be found here: https://docs.google.com/spreadsheets/d/1D9a1m6X9L8kFtlCAaL7xc-PCU2UZiZJMb7s9seydlno/edit?usp=sharing

Bidding is done as the following:
 - One with any ace
 - Two with ace and deuce
 - Three with ace, deuce, and at least four trump total
 - Cinch with AKQJ2
 - Otherwise, lowest legal bid.

Attributes:
  * The following attributes are mandatory for all AI models. Note the double-
    underscores.
  AI_CLASS (str): The name of the AI class. This *must* match the name of the
    class that extends AIBase.
  __author__ (str): AI author/designer's name.
  __version__ (str): Version information for model.
  __date__ (str): Release date for model.
  __skill__ (str): Skill level/description of AI, used for informing AI
    selection by players.
  __agent_name__ (str): Name of AI agent. This is used for display and logging
    purposes and may differ from AI_CLASS.
  __description__ (str): Brief description of AI. This may include highlights
    of its logic, any special techniques, or other info that may be of interest
    to users.

Public classes:
  Goofus: AI model with minimal skill.
  Rule: Rule to be run when determining what card to play.

"""

#TODO: make everything docstring compliant

import random

# Import base class for AI agent
from ai.base import AIBase, log

AI_CLASS = "Goofus"  # Set this to match the class name for the agent
__author__ = "JackieChiles"
__version__ = "1.1"
__date__ = "4 December 2014"
__skill__ = "1"
__agent_name__ = "Goofus"
__description__ = "Goofus will make decisions at a very basic level when playing and bidding, using only the current game state."


class Goofus(AIBase):
    def __init__(self, room, seat):
        """Initialize AI agent. Blocks thread.

        All agents *must* include a super() call like below, and must have
        `self.start()` as the final line of their __init__ method.

        Args:
          room (int): Target room number.
          seat (int): Target seat number within room.
          bidSuit (int): Suit on which bid was made this hand

        """
        super(Goofus, self).__init__(room, seat, self.identity)
        self.start()  # Blocks thread
        self.bidSuit = None
        self.legalPlays = []

    def bid(self):
        """Overriding base class bid."""
        maxBid = 0
        maxBidCount = 0
        faceCount = len(filter(lambda c: c.rank > 10, self.hand))

        # Find the highest possible bid
        for suit in range(4):
            a = len(filter(lambda c: c.suit == suit and c.rank == 14, self.hand)) > 0
            k = len(filter(lambda c: c.suit == suit and c.rank == 13, self.hand)) > 0
            q = len(filter(lambda c: c.suit == suit and c.rank == 12, self.hand)) > 0
            j = len(filter(lambda c: c.suit == suit and c.rank == 11, self.hand)) > 0
            d = len(filter(lambda c: c.suit == suit and c.rank == 2, self.hand)) > 0
            count = len(filter(lambda c: c.suit == suit, self.hand))

            # Decision on bid value for each suit made as described above
            if a and k and q and j and d:
                bid = 5
            elif (a and d and count > 3) or (k and d and count > 3 and faceCount > 3):
                bid = 3
            elif (a and d) or (k and d and count > 3) or (a and count > 3):
                bid = 2
            elif a or ((k or q) and (faceCount > 3 or count > 2)):
                bid = 1
            else:
                bid = 0

            # If this suit can get a higher bid, or the same bid but with more 
            # cards of the suit in hand, choose this suit.
            if bid > maxBid or (bid == maxBid and count > maxBidCount):
                maxBid = bid
                maxBidCount = count
                self.bidSuit = suit

        # Just pass if the chosen bid was not legal (base.py will handle illegal pass as stuck dealer)
        if self.is_legal_bid(maxBid):
            self.send_bid(maxBid)
        else:
            self.send_bid(0)

    def play(self):
        """Overriding base class play."""

        # Determine the set of legal plays. Goofus ignores everything else.
        self.legalPlays = filter(lambda c: self.is_legal_play(c), self.hand)

        # Short circuit if there's only one legal play
        if len(self.legalPlays) == 1:
            self.send_play(self.legalPlays[0])
            return

        # If Goofus leading on first trick, set gamestate's trump to suit on which bid was based
        # This is a bit hacky, but allows all references for self.gs.trump to work
        if self.conIsMyLeadFirstTrick():
            self.gs.trump = self.bidSuit

        #TODO: Try not to lead suits that would leave bare tens

        # Set up the rules to determine what to play
        rules = [
            Rule(self.conIsMyLeadFirstTrick,
                 False,
                 [
                     (self.ft, True),
                     (self.lt, True),
                     (self.tt, True),
                     (self.jt, True),
                     (self.fn, True),
                     (self.tn, True),
                     (self.ln, True)
                 ]),
            Rule(self.conIsMyLead,
                 False,
                 [
                     (self.ft, True),
                     (self.fn, True)
                 ]),
            Rule(self.conMyPlayLastParterTaking,
                 False,
                 [
                     (self.jt, False),
                     (self.tn, False),
                     (self.tt, False),
                     (self.fn, True),
                     (self.ln, False),
                     (self.lt, False),
                     (self.ft, False)
                 ]),
            Rule(self.conMyPlayLastPartnerNotTakingJackTrumpOrTenShowing,
                 True,
                 [
                     (self.jt, False),
                     (self.tn, False),
                     (self.tt, False),
                     (self.ln, False),
                     (self.fn, False),
                     (self.lt, False),
                     (self.ft, False)
                 ]),
            Rule(self.conMyPlayLastPartnerNotTaking,
                 True,
                 [
                     (self.jt, False),
                     (self.tn, False),
                     (self.tt, False)
                 ]),
            Rule(self.conPartnerShowingAceTrump,
                 False,
                 [
                     (self.jt, False),
                     (self.tn, False),
                     (self.tt, False)
                 ]),
            Rule(self.conMyPlaySecondOrThirdJackTrumpOrTenShowing,
                 True,
                 [
                     (self.ft, True),
                     (self.lt, True),
                     (self.fn, True),
                     (self.ln, True),
                     (self.tt, False)
                 ]),
            Rule(self.conDefault,
                 False,
                 [
                     (self.ln, False),
                     (self.lt, False),
                     (self.fn, False),
                     (self.ft, False),
                     (self.tn, False),
                     (self.tt, False),
                     (self.jt, False)
                 ])
        ]

        # Run each rule in order and play the first matching card hit
        for i, rule in enumerate(rules):
            matchingCards = rule.evaluate(self)
            if len(matchingCards) > 0:
                self.send_play(matchingCards[0])
                return

    def think(self):
        """Overriding base class think."""
        pass

    """Helper methods

    Helper methods used in conditions, rules processing, or elsewhere.
    """

    def whoWinsTrick(self, cards, gs=None): # Shamelessly copied from HAL. Things like this might ultimately go in AI base, I would think.
        """Return the card that wins the trick.

        `cards[0]` must be the card led.

        This method is largely copied from core.gamestate.

        Args:
          cards (list): Card objects representing the trick, in player order
            starting with whoever led. Indeed, this variable name creates a
            namespace conflict with the cards module, but this method doesn't
            use that module.
          gs (GameState, default=self.gs): GameState used to make decision.

        Returns:
          Card: The Card object that wins the trick.

        """
        if gs is None:
            gs = self.gs

        # Determine which suit wins the trick
        if self.gs.trump in map(lambda x: x.suit, cards):
            winning_suit = self.gs.trump
        else:
            winning_suit = cards[0].suit

        # Find the winning card and determine who played it
        current_highest_card_rank = 0
        for card in cards:
            if card.suit == winning_suit:
                if card.rank > current_highest_card_rank:
                    current_highest_card_rank = card.rank
                    current_highest_card = card
        return current_highest_card

    def isThisWinner(self, card):
        return self.whoWinsTrick(self.gs.cardsInPlay + [card]) == card

    def getPartnerCard(self):
        # Partner hasn't played yet
        if len(self.gs.cardsInPlay) < 2:
            return None

        if len(self.gs.cardsInPlay) == 2:
            return self.gs.cardsInPlay[0]
        else: # Three cards in play
            return self.gs.cardsInPlay[1]

    def isPartnerWinningTrick(self):
        partnerCard = self.getPartnerCard()

        if partnerCard is None:
            return False
        else:
            return self.whoWinsTrick(self.gs.cardsInPlay) == partnerCard

    def isMyPlayLast(self):
        return len(self.gs.cardsInPlay) == 3

    def isJackTrumpOrTenShowing(self):
        return len(filter(lambda c: c.rank == 10 or (c.rank == 11 and c.suit == self.gs.trump), self.gs.cardsInPlay)) > 0

    """Conditions

    Each condition should return a boolean value based on parameters of the current game state or 
    other conditions.
    """

    def conIsMyLead(self):
        return len(self.gs.cardsInPlay) == 0

    def conIsMyLeadFirstTrick(self):
        return self.conIsMyLead() and len(self.hand) == 9

    def conMyPlayLastParterTaking(self):
        return self.isMyPlayLast() and self.isPartnerWinningTrick()

    def conMyPlayLastPartnerNotTakingJackTrumpOrTenShowing(self):
        return self.conMyPlayLastPartnerNotTaking() and self.isJackTrumpOrTenShowing()

    def conMyPlayLastPartnerNotTaking(self):
        return self.isMyPlayLast() and not self.isPartnerWinningTrick()

    def conPartnerShowingAceTrump(self):
        partnerCard = self.getPartnerCard()

        if partnerCard is None:
            return False
        else:
            return partnerCard.suit == self.gs.trump and partnerCard.rank == 14

    def conMyPlaySecondOrThirdJackTrumpOrTenShowing(self):
        return (len(self.gs.cardsInPlay) == 1 or len(self.gs.cardsInPlay) == 2) and self.isJackTrumpOrTenShowing()

    def conDefault(self):
        return True

    """Card classes

    Cards are divided into the following seven classes:
     - FT - Face trump
     - JT - Jack trump
     - TT - Ten trump
     - LT - Low trump
     - FN - Face non-trump
     - TN - Ten non-trump
     - LN - Low non-trump

    The card class methods will return cards from the set of legal plays for each class.
    """

    def ft(self):
        return filter(lambda c: c.rank > 11 and c.suit == self.gs.trump, self.legalPlays)

    def jt(self):
        return filter(lambda c: c.rank == 11 and c.suit == self.gs.trump, self.legalPlays)

    def tt(self):
        return filter(lambda c: c.rank == 10 and c.suit == self.gs.trump, self.legalPlays)

    def lt(self):
        return filter(lambda c: c.rank < 10 and c.suit == self.gs.trump, self.legalPlays)

    def fn(self):
        return filter(lambda c: c.rank > 10 and c.suit != self.gs.trump, self.legalPlays)

    def tn(self):
        return filter(lambda c: c.rank == 10 and c.suit != self.gs.trump, self.legalPlays)

    def ln(self):
        return filter(lambda c: c.rank < 10 and c.suit != self.gs.trump, self.legalPlays)

class Rule(object):
    def __init__(self, condition, filterToWinners, cardClasses):
        """Initializes the rule.

        Args:
          condition (func): Must return a boolean value. If the condition is met,
            the evaluate method will look for matching cards to return.
          filterToWinners (boolean): True if cards should only be returned if
            they would win the trick
          cardClasses (list): List of two-item tuples containing a func and a
            boolean value. The func must return a list of cards, and the boolean
            should be True if the returned cards should be sorted descending.
        """

        self.condition = condition
        self.filterToWinners = filterToWinners
        self.cardClasses = cardClasses

    def evaluate(self, agent):
        """Evaluates the rule.

        If the condition is met, each given card class is
        searched for matching cards. A list of zero or more matching cards is
        returned.

        Args:
          agent: AI agent calling the rule.

        Returns:
          List: Zero or more cards from hand that satisfy the rule.
        """

        # If the condition is true, look at each specified card class in order.
        # Return the filtered and sorted set of matching cards if any are found.
        if self.condition():
            for cardClass in self.cardClasses:
                matchingCards = cardClass[0]()

                if self.filterToWinners:
                    matchingCards = filter(lambda c: agent.isThisWinner(c), matchingCards)

                matchingCards = self.sortCards(matchingCards, cardClass[1])

                if len(matchingCards) > 0:
                    return matchingCards

        # If the condition is false or no matching cards were found, return empty list
        return []

    def sortCards(self, cardsToSort, descending=False):
        return sorted(cardsToSort, key=lambda c: c.rank, reverse=descending)
