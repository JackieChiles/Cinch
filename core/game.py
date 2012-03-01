#!/usr/bin/python3
"""
no comment
"""
import random

import common as common
from player import Player
import cards
from gamestate import GameState

#Constants and global variables
STARTING_HAND_SIZE = 9
NUM_PLAYERS = 4
GAME_MODE = common.enum(PLAY=1, BID=2)
TEAM_SIZE = 2

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
            [(p.name, p.id) for p in self.players])

    def set_game_id(self):      #may be unneeded
        """Access external tracker to get new game id and set variable."""

    def create_players(self):   #revise this;
        """
        Instantiate Player objects based on args, pack into array,
        and set internal variable.
        """

    def check_play_legality(self, player, card):
        """Check a proposed play for legality against the current gamestate.
        Assumes that player is indeed the active player.
        """
        
        if card not in player.hand:
            return False
        if len(self.gamestate['cards_in_play']) == 0:
            return True # No restrictions on what cards can be led.
        if card.suit is self.gamestate['trump']:
            return True # Trump is always OK    
        if card.suit is self.gamestate['cards_in_play'][0].suit:
            return True # Not trump, but followed suit.
        for each_card in player.hand:
            if each_card.suit is self.gamestate['cards_in_play'][0].suit:
                return False # Could have followed suit with a different card.
                
        # The above conditions should catch everything, shouldn't get here.
        assert 0
        
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
        play = play_msg.data['card'] # will this be Card or just int?
        # Also, if Card, will it be a copy of the actual Card created by Game?
        # I'm a bit foggy on that right now.

        ###########
        # Invoke play processing logic and return game state updates
        # to here. [We will use dicts for comm with router. JBG]
        # Game router will ensure message follows Comm Structure contract, so
        # formatting data here IAW those guidelines is optional but a good idea
        ###########
        
        # Does active player need to be verified in this method? Or will it be
        # 100% handled by the router before even checking the contents of the
        # message, as in the workflow diagram? Couldn't hurt to check twice, I
        # guess.

        if check_play_legality(player_id, play):
            pass # It's a legal play; do stuff here.
        else:
            pass # Not a legal play; chastise appropriately
            
            
        #######
        # Contruct return dicts down here after moving stuff around and marking
        # it appropriately
        # if play was illegal, send error response to single client
        #    return {'err': 'Illegal play.'}
        #elif play was legal, return 2 GS update info set types: (router will
        #take care of Message assembly and addressing)
        ##-one with private info (card removed from hand, new hand if applic)
        ##---for each private message, include the local player number
        ##-one with public info to all
        ##---per executive order, if there is one private message, then there
        ##      are no public messages -- each client should only get 1
        ##      message per player move
        #
        # this should gather all info needed to describe the new game state.
        # do end-of-hand/tricks within play processing; the client will render
        # actions in the proper order, just by sending one message (i.e. don't
        # use different message for card play, end of trick, and new hand).

        return

#test
if __name__ == '__main__': 
    print("Creating new game with 4 players.")
    g = Game()
    g.players = [Player(x) for x in range(4)]
    print(g)
    g.deal_hand()
    print("Undealt cards:",g.deck)
    print("players[2].hand=",g.players[2].hand)
    g.gamestate = GameState(42042)
    print(g.check_play_legality(g.players[2],g.players[2].hand[3]))
