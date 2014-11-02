#!/usr/bin/python2
"""Game log parser for Cinch."""

import ast
from collections import defaultdict

import logging
log = logging.getLogger()

PLAYER_COUNT = 4


def prepare(gameData, events):
    """Prepare game log data for client.

    Args:
      gameData (DAL.Row): The game's row from db.Games. This contains player
        names, the game ID, and the game's timestamp.
      events (DAL.Rows): List of all the event rows from db for this game.

    Returns:
      dict: The prepared game log data, containing the keys `gameData`,
        and `hands`. Both are dicts themselves.

    """
    log.info('Preparing game log for game id {0}.'.format(gameData.id))

    # Convert event strings into dictionaries
    for x in events:
        x.Event = ast.literal_eval(x.EventString)

    # Split data into hands
    eventsByHand = defaultdict(list)
    for x in events:
        eventsByHand[x.HandNumber].append(x)

    # Only storing __dict__ to give greenlet something JSON-serializable
    hands = map(lambda x: Hand(*x).__dict__, eventsByHand.items())

    gameData.winner = filter(
        lambda x: 'win' in x.Event, events)[0].Event['win']
    gameData.finalScores = hands[-1]['totalPoints']

    return dict(gameData=gameData.as_dict(), hands=hands)


class Hand(object):

    """Helper class for parsing game logs.

    Attributes:
      num (int): The hand number within the game.
      trump (int): The trump for the hand.
      bids (dict): With the keys:
        - values (list): Bid amounts in pNum order (list index == pNum).
        - dealer (int): pNum of dealer.
        - winner (int): pNum of bid winner.
      tricks (list): Each element is a dict with keys:
        - values (list): Cards played in pNum order.
        - leader (int): pNum of player that led trick.
        - winner (int): pNum of trick winner.
      points (dict): With keys `game`, `jack`, `high`, `low` and values of
        the team number that got that point, or None if no one got it.
      gamePoints (list): Game points for this hand in team order.
      totalPoints (list): Total points after this hand in team order.

    """

    def __init__(self, num, events):
        """Process events and store hand data.

        Args:
          num (int): Hand number
          events (list): List of events for this hand.

        """
        self.num = num

        # When a hand ends, 4 log entries are generated for sending private
        # info to each player. Here, we only care about the public information,
        # so we condense these messages by erasing the mostly-duplicate events.
        for i, x in enumerate(events):
            if 'addC' in x.Event:
                for y in range(i+1, i+PLAYER_COUNT):
                    events[y].Event = dict()

        bidRows = filter(lambda x: 'bid' in x.Event, events)
        playRows = filter(lambda x: 'playC' in x.Event, events)
        scoreRow = filter(lambda x: 'sco' in x.Event, events)[0]

        self.setBids(bidRows)
        self.setTricks(playRows)
        self.trump = filter(
            lambda x: 'trp' in x.Event, playRows)[0].Event['trp']
        self.setScores(scoreRow)

    def setBids(self, bids):
        """Set the bids attribute for the Hand.

        The 'actvP' in the final bid is the bid winner.

        Args:
          bids (list): The Rows containing bid data for this hand.

        """
        values = [None] * len(bids)
        for b in bids:
            values[b.Event['actor']] = b.Event['bid']

        dealer = bids[0].Event['actor']
        winner = bids[-1].Event['actvP']

        self.bids = dict(values=values, dealer=dealer, winner=winner)

    def setTricks(self, plays):
        """Set the tricks attribute for the Hand.

        Args:
          plays (list): The Rows containing play data for this hand.

        """
        self.tricks = []

        leader = winner = 0
        values = [0] * PLAYER_COUNT
        first = True
        for i in range(len(plays)):
            e = plays[i].Event
            values[e['actor']] = e['playC']

            if first:
                leader = e['actor']
                first = False

            elif 'remP' in e:
                winner = e['remP']
                self.tricks.append(dict(values=values, leader=leader,
                                        winner=winner))
                leader = winner = 0
                values = [0] * PLAYER_COUNT
                first = True

    def setScores(self, row):
        """Set score-related attributes for the Hand.

        Args:
          row (Row): The score data for this hand.

        """
        self.gamePoints = row.Event['gp']
        self.totalPoints = row.Event['sco']

        handPoints = dict(zip(['high', 'low', 'jack', 'game'], [None]*4))
        for i, x in enumerate(row.Event['mp']):
            if 'h' in x:
                handPoints['high'] = i
            if 'l' in x:
                handPoints['low'] = i
            if 'j' in x:
                handPoints['jack'] = i
            if 'g' in x:
                handPoints['game'] = i

        self.points = handPoints
