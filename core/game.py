#!/usr/bin/python3
"""
no comment
"""
import random

import core.common as common
from core.player import Player
import core.cards


#Constants and global variables
STARTING_HAND_SIZE = 9
NUM_PLAYERS = 4
GAME_MODE = common.enum(PLAY=1, BID=2)

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

    def set_game_id(self):      #may be unneeded
        """Access external tracker to get new game id and set variable."""

    def create_players(self):   #revise this;
        """
        Instantiate Player objects based on args, pack into array,
        and set internal variable.
        """

    def deal_hand(self):
        """Deal new hand to each player and set card ownership."""
        for player in self.players:
            player.hand = [self.deck.deal_one()
                           for x in range(STARTING_HAND_SIZE)]
            
            for card in player.hand:
                card.owner = player.id

    def handle_card_played(self, play_msg):
        """Invoke play processing logic on incoming play and send update to
        clients, or indicate illegal play to single player.

        play_msg (Message): contains local player id and card played by player

        """
        player_id = play_msg.source
        play = play_msg.data['card']

        ###########
        # Invoke play processing logic and return game state updates
        # to here. Could be dict, tuple, etc. To be established
        # by Mr. Poodlepants. Following code will be modified to reflect that.
        # Game router will ensure message follows Comm Structure contract, so
        # formatting data here IAW those guidelines is optional.
        ###########

        #if play was illegal, send error response to single client

        #elif play was legal, return 2 GS update info set types: (router will
        #take care of Message assembly and addressing, just need local id)
        ##-one with private info (card removed from hand, new hand if applic)
        ##---for each private message, include the local player number
        ##-one with public info to all
        ##--your choice: have one-size-fits-all public message and take care
        ##      not to duplicate data in private messages, sending both; or
        ##      send one customized private&public msg to each client
        #
        # this should gather all info needed to describe the new game state.
        # do end-of-hand/tricks within play processing; the client will render
        # actions in the proper order, just by sending one message (i.e. don't
        # need different message for card play, end of trick, and new hand).

        return

#test
if __name__ == '__main__': 
    print("Creating new game with 4 players.")
    g = Game()
    g.players = [Player() for x in range(4)]
    print(g)
    g.deal_hand()
    print("Undealt cards:",g.deck)
    print("players[0].hand=",g.players[0].hand)
