#!/usr/bin/python2
"""HAL: A simple but slightly thoughtful good AI.

HAL uses simple algorithms to decide how to play and bid. It does not learn on
its own. It does not currently consider game points at all, and while it
considers the Jack during bidding, it does not consider it during play.
AI-on-AI testing shows that HAL is better than Rand and JoeLowbid.

Here's a summary of the rules HAL uses:

- For each suit, predict the points HAL could win based on its hand.
--- For high card, 1 point for Ace, 1/3 point for King
--- For low card, 1 point for Two, 1/3 point for Three
--- For Jack, 1/3 point for each card in suit with higher rank; must have Jack
--- Does not consider game points
- Bid the highest predicted points, rounded down, across all suits
- If HAL wins the bid, lead with the highest card from the suit that drove bid.
- If leading trick (not hand), play highest rank card, off-trump if possible.
- If playing 2nd, play strongest card if HAL can win, otherwise play weakest.
- If playing 3rd, choose play based on the cards in play and the number of
  possible ways the 4th player could beat HAL's team for each possible play.
- If playing 4th, play the weakest card that will let HAL's team win, if
  possible; play the weakest card period otherwise.

Attributes:
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
  HAL: AI model for random gameplay.

"""

import math

from collections import defaultdict

import core.cards as cards

# Import base class for AI agent
from ai.base import AIBase, log

AI_CLASS = "HAL"  # Set this to match the class name for the agent
__author__ = "Mike"
__version__ = "1.0"
__date__ = "22 November 2014"
__skill__ = "1"
__agent_name__ = "HAL"
__description__ = "I would like to play a game."


class HAL(AIBase):
    def __init__(self, room, seat):
        """Initialize AI agent. Blocks thread.

        All agents *must* include a super() call like below, and must have
        `self.start()` as the final line of their __init__ method.

        Args:
          room (int): Target room number.
          seat (int): Target seat number within room.

        """
        super(HAL, self).__init__(room, seat, self.identity)

        self.trackedPlays = defaultdict(list)
        self.targetTrump = None

        self.start()  # Blocks thread

    def applyUpdate(self, msg):
        """Overriding base clase applyUpdate to better monitor game actions."""
        super(HAL, self).applyUpdate(msg)

        if 'addC' in msg:
            # New hand, so clear tracked plays
            self.trackedPlays = defaultdict(list)

        if 'playC' in msg:
            # Want to keep track of who plays what during a hand
            self.trackedPlays[msg['actor']].append(cards.Card(msg['playC']))

    def bid(self):
        """Overriding base class bid.

        Bids based on estimated ability to score points, while considering
        bids of other players.

        >....Really, I should figure out confidence intervals for each legal
        bid or something to that effect

        """
        # Determine ideal bid based soley on own hand
        predictedPointsBySuit = dict()
        for s in cards.SUITS:
            predictedPointsBySuit[s] = self.predictPointsFromHandBySuit(s)
        maxPoints = max(predictedPointsBySuit.items(),
                        key=lambda x: predictedPointsBySuit[x[0]])
        b = maxPoints[1]

        # TODO consider game point potential -- ability to get other ppls 10s
        # based on how many of trump I have...
        pass

        # Modify ideal bid based on current bids and match points...? TODO
        pass

        # Test for legality and make ideal bid if legal, or pass
        b = int(math.floor(b))  # Can change to round() for slightly more aggro

        if b > 0:
            self.targetTrump = maxPoints[0]
        else:
            self.targetTrump = None

        if self.is_legal_bid(b):
            self.send_bid(b)
        else:
            if self.gs.dealer == self.pNum:
                self.send_bid(1)  # Minimum bid required as stuck dealer
            else:
                self.send_bid(0)

    def play(self):
        """Overriding base class play.

        Plays card that improves chances of team taking the trick.

        """
        # If I'm leading the hand, then lead with targetTrump, determined
        # during bidding.
        if len(self.gs.cardsInPlay) == 0 and len(self.gs.takenCards) == 0:
            c = self.determinePlayOnHandLead()
        else:
            c = self.determinePlay()

        self.send_play(c)

    def think(self):
        """Overriding base class think."""
        pass

    # ---------

    def determinePlayOnHandLead(self):
        """Return play for when I am leading the hand."""
        if self.targetTrump is None:
            # Ideal bid was to pass, so lead with most populous suit
            suit_count = dict()
            map(lambda s: suit_count.__setitem__(
                s, len(filter(lambda x: x.suit == s), self.hand)),
                cards.SUITS)
            self.targetTrump = max(
                suit_count.items(), key=lambda x: suit_count[x[0]])[0]

        targets = filter(lambda x: x.suit == self.targetTrump, self.hand)
        return targets[0]  # [0] is highest rank

    def determinePlay(self):
        """Return play for when I am not leading the hand."""
        legalCards = filter(self.is_legal_play, self.hand)

        # Sort by descending rank
        legalCards.sort(key=lambda x: x.rank, reverse=True)

        if len(self.gs.cardsInPlay) == 3:
            # I am last to act this trick, so I know with certainty the result
            # of my play. Rule: play lowest rank card that will allow my team
            # to win the trick; if possible, play off-trump to do so. If we
            # can't win the trick, play lowest rank card period; if possible,
            # play off-trump.
            # self.gs.cardsInPlay[1] is the card played by my partner
            winningPlays = filter(
                lambda x: self.whoWinsTrick(self.gs.cardsInPlay + [x]) in
                [self.gs.cardsInPlay[1], x], legalCards)
            if len(winningPlays) == 0:
                # Can't win this trick; play off-trump if possible
                trumpCards = filter(
                    lambda x: x.suit == self.gs.trump, legalCards)
                offTrumpCards = filter(
                    lambda x: x.suit != self.gs.trump, legalCards)

                if len(offTrumpCards) == 0:
                    # I have to play trump yet lose the trick
                    targets = trumpCards
                else:
                    # I can play off-trump and lose the trick
                    targets = offTrumpCards
            else:
                # Can win this trick; do it off-trump if possible
                trumpCards = filter(
                    lambda x: x.suit == self.gs.trump, winningPlays)
                offTrumpCards = filter(
                    lambda x: x.suit != self.gs.trump, winningPlays)

                if len(offTrumpCards) == 0:
                    # I can win but must play trump
                    targets = trumpCards
                else:
                    # I can win by playing off-trump
                    targets = offTrumpCards
            return targets[-1]  # Cards are ordered by rank high to low

        elif len(self.gs.cardsInPlay) == 0:
            # I am leading the trick but not the hand (that's handled
            # elsewhere). Rule: play highest rank card period; if possible,
            # play off-trump to do so (save trump for later).
            offTrumpCards = filter(
                lambda x: x.suit != self.gs.trump, legalCards)
            if len(offTrumpCards) == 0:
                # Have to play a trump
                return legalCards[0]
            else:
                return offTrumpCards[0]

        elif len(self.gs.cardsInPlay) == 2:
            # I am playing 3rd. My partner led, so I should try to support his
            # play. There is uncertainty on what the next player will play.
            # Based on the current board and my legal plays, there's a
            # manageable set of possible outcomes, since only a certain set of
            # cards can change the outcome. Rule: If we lose the trick based on
            # the opponent's card, play a weak card.
            # Otherwise, for each legal play of
            # mine, determine the set of cards the last player could play to
            # win the trick based on seen cards; then
            # play the card that minimizes his win odds; in case of
            # ties, play the weakest card, off-trump if possible.
            oppCard = self.gs.cardsInPlay[1]
            playsThatBeatOppCard = filter(lambda x: self.whoWinsTrick(
                self.gs.cardsInPlay + [x, oppCard]) != oppCard, legalCards)
            weWillLoseTrick = True if len(playsThatBeatOppCard) == 0 else False

            if weWillLoseTrick:
                # Definitely can't win, so play weak card
                offTrumpCards = filter(
                    lambda x: x.suit != self.gs.trump, legalCards)
                if len(offTrumpCards) == 0:
                    return legalCards[-1]
                else:
                    return offTrumpCards[-1]

            else:
                # Might not lose trick; depends on what the 2nd opp can play
                # For each card in playsThatBeatOppCard, determine what cards
                # the 2nd opponent could play that wins the trick. We don't
                # need to check cards of mine that don't beat my partner (same
                # suit, lower rank).
                partnerCard = self.gs.cardsInPlay[0]
                options = list()
                for c in playsThatBeatOppCard:
                    if c.suit == partnerCard.suit and \
                       c.rank < partnerCard.rank:
                        continue
                    else:
                        waysToLose = self.getUnseenCardCodesThatWinTrick(
                            [partnerCard, oppCard, c])
                        options.append((c, waysToLose))

                if len(options) == 0:
                    # No card that beats 1st opp card is better than partner's
                    # card, so I can't strengthen his play. Play weakly.
                    return playsThatBeatOppCard[-1]
                else:
                    minWaysToLose = min(map(lambda x: x[1], options))
                    targetOptions = filter(lambda x: x[1] == minWaysToLose,
                                           options)
                    return targetOptions[-1][0]  # Pick weakest card of set
        else:
            # I am playing 2nd, so my partner will play last. This is the worst
            # position, since there are two pending uncertain plays, and I need
            # to be a good partner. Rule: If I can beat the opponent's card,
            # play the strongest card that will do so. Otherwise, play weakly.
            ledCard = self.gs.cardsInPlay[0]
            strongCards = filter(
                lambda x: self.beatsCard(ledCard, x, ledCard.suit), legalCards)
            if len(strongCards) == 0:
                return legalCards[-1]
            else:
                return strongCards[0]

    def beatsCard(self, theirCard, myCard, suitLed):
        """Return boolean of if myCard beats theirCard.

        This does not look at winning a trick, only if the card wins 1 v. 1
        while considering the suit led.

        Args:
          theirCard (Card): The card I'm trying to beat.
          myCard (Card): The card I'm considering playing.
          suitLed (int): The suit of the lead card.

        Returns:
          boolean: True if myCard beats theirCard, False otherwise.

        """
        mySuit = myCard.suit
        theirSuit = theirCard.suit

        if theirSuit == self.gs.trump:
            if mySuit == self.gs.trump:
                return myCard.rank > theirCard.rank
            else:
                return False
        elif mySuit == self.gs.trump:
            return True
        else:
            # Neither played trump
            if theirSuit == suitLed:
                if mySuit == suitLed:
                    return myCard.rank > theirCard.rank
                else:
                    return False
            else:
                if mySuit == suitLed:
                    return True
                else:
                    return False

    def getUnseenCardCodesThatWinTrick(self, trickCards):
        """Return list of card codes that would win a trick, given 3 cards.

        This makes use of the tracked cards and cards in my hand, targeting
        only cards that I have not seen.

        A card must be trump or a higher-rank of the led suit (if trump
        not led), or a higher-rank trump if trump was led.

        Args:
          trickCards (list): Card objects. The first must be the led card.

        Returns:
          list: Card codes that would win the trick.

        """
        trumpLed = True if trickCards[0].suit == self.gs.trump else False
        winners = []
        if trumpLed:
            topTrump = max(filter(lambda x: x.suit == self.gs.trump,
                                  trickCards), key=lambda x: x.rank)
            winningRanks = filter(lambda x: x > topTrump.rank, cards.RANKS)
            winners = map(lambda x: cards.RS_TO_CODE[(x, self.gs.trump)],
                          winningRanks)
        else:
            # Start with all trump cards
            winners = map(lambda x: cards.RS_TO_CODE[(x, self.gs.trump)],
                          cards.RANKS)

            topLed = max(filter(lambda x: x.suit == trickCards[0].suit,
                                trickCards), key=lambda x: x.rank)
            winningRanks = filter(lambda x: x > topLed.rank, cards.RANKS)
            winners.extend(list(map(
                lambda x: cards.RS_TO_CODE[(x, trickCards[0].suit)],
                winningRanks)))

        # Filter out seen card codes
        allTrackedPlays = []
        map(lambda x: allTrackedPlays.extend(self.trackedPlays[x]),
            self.trackedPlays)
        trackedCodes = map(lambda x: x.code, allTrackedPlays)
        return filter(lambda x: x in trackedCodes, winners)

    def whoWinsTrick(self, cards, gs=None):
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

    def predictPointsFromHandBySuit(self, suit):
        """Predict the number of points the AI could take based on own hand.

        The assumptions of this method are based on the prior assumption that
        the AI does not neccessiarly win the bid.

        Aces and Twos are automatic points for the suit. If no Ace, then King
        is worth half a point; if no Two, then Three is worth 1/3 points. No
        other cards are considered for High/Low points.

        Jacks are weighted by the number of cards > Jack in the suit (AJ is
        riskier than AKQJ). A naked Jack is only considered valuable if the
        AI wins the bid, so it is not counted here.

        Game points are not suit-dependant so are handled elsewhere.

        Args:
          suit (int): Suit number based on core.cards.SUITS.

        Returns:
          float: Predicted number of points in the interval [0, 3]

        """
        points = 0
        cards = filter(lambda x: x.suit == suit, self.hand)
        ranks = map(lambda x: x.rank, cards)
        if 14 in ranks:  # Ace
            points += 1
        elif 13 in ranks:  # King
            points += 0.33

        if 2 in ranks:
            points += 1
        elif 3 in ranks:
            points += 0.33

        if 11 in ranks:  # Jack
            guards = filter(lambda x: x > 11, ranks)  # len in [0, 3]
            points += len(guards) / float(3)

        return points
