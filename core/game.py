#!/usr/bin/python3
"""
no comment
"""
import random

import core.common
from core.player import Player
import core.cards


#Constants and global variables
STARTING_HAND_SIZE = 9
NUM_PLAYERS = 4
GAME_MODE = enum(PLAY_MODE=1, BID_MODE=2)

# Bid constants
BID_PASS = 0
BID_CINCH = 5


class Game:
    """
    Define object for Game object with instance variables:
        id (integer): unique id for game object
        mode (integer): setting for game mode
        players (list): array of Player objects for players in game
        teams (dict): player id : local player num pairings (?)
        gamestate (object): current game state
        deck (object): Deck object containing Card objects
        
    """
    def __init__(self): #pass newGame params as args
        self.id = 0     #have external counter for this
        self.players = []
        self.gamestate = None
        self.deck = cards.Deck()

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Cinch game with players: {0}".format(
            [p.name for p in self.players])

    def set_game_id(self):
        """Access external tracker to get new game id and set variable."""

    def create_players(self):   #will need to pass stuff into this
        """
        Instantiate Player objects based on args, pack into array,
        and set internal variable.
        """

    def set_player_ids(self):
        """Set random ids for player objects."""
        ids = [random.randint(0,1023) for x in range(len(self.players))]

        if len(set(ids)) == len(self.players):
            #All created ids unique, so set value in Player objects
            for player in self.players:
                player.id = ids.pop()

        else:
            #Not enough ids, so try again
            self.set_player_ids()

    def deal_hand(self):
        """Deal new hand to each player and set card ownership."""
        for player in self.players:
            player.hand = [self.deck.deal_one()
                           for x in range(STARTING_HAND_SIZE)]
            
            for card in player.hand:
                card.owner = player.id


#test
if __name__ == '__main__': 
    print("Creating new game with 4 players.")
    g = Game()
    g.players = [Player() for x in range(4)]
    print(g)
    g.set_player_ids()
    g.deal_hand()
    print("Undealt cards:",g.deck)
    print("players[0].hand=",g.players[0].hand)
