#!/usr/bin/python3
"""
Game object for managing game properties, players, and game states.

TODO: game logging functionality
      pickling game for later recovery

"""
import random

#this allows game.py to be ran alone from core dir AND as part of cinch.py
# for development.
## once final, will use only absolute imports (core.*)
try:
    import common as common
    from player import Player
    import cards
    from gs import gs
except ImportError:
    import core.common as common
    from core.player import Player
    import core.cards as cards
    from core.gs import gs    

#Constants and global variables
STARTING_HAND_SIZE = 9
NUM_PLAYERS = 4
GAME_MODE = common.enum(PLAY=1, BID=2)
TEAM_SIZE = 2

# Bid constants
BID = common.enum(PASS=0, CINCH=5)


class Game:
    """
    Define object for Game object with instance variables:
        id (integer): unique id for game object
        mode (integer): setting for game mode
        players (list): array of Player objects for players in game
        teams (dict): player id : local player num pairings (?)
        gs (object): current game state
        deck (object): Deck object containing Card objects
        
    """
    def __init__(self): #pass newGame params as args (??)
        self.id = 0     #TODO: have external counter for this
        self.players = []
        self.gs = None
        self.deck = cards.Deck()

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Cinch game with players: {0}".format(
            [(p.name, p.pNum) for p in self.players])
        
    def create_players(self):
        """
        Instantiate Player objects based on args, pack into array,
        and set internal variable.

        """
        #if there is nothing more to do here, put line in start_game and
        #remove this method.
        self.players = [Player(x) for x in range(NUM_PLAYERS)]

    def check_play_legality(self, player, card_num):
        """Check a proposed play for legality against the current gs.
        Assumes that player is indeed the active player.

        player (Player): player object of player playing a play
        card_num (int): encoding of card to be played by player

        """
        # Search player's hand for card where card_num = card.code
        ##MJG: I just added the card.code functionality for convenience.
        has_card = False
        for card in player.hand:
            if card.code == card_num:
                has_card = True
                break

        if not has_card:
            return False
        
        if len(self.gs.cards_in_play) == 0:
            return True # No restrictions on what cards can be led.
        if card.suit is self.gs.trump:
            return True # Trump is always OK
        if card.suit is self.gs.cards_in_play[0].suit:
            return True # Not trump, but followed suit.
        for each_card in player.hand:
            if each_card.suit is self.gs.cards_in_play[0].suit:
                return False # Could have followed suit with a different card.
                
        # The above conditions should catch everything, shouldn't get here.
        assert 0
        
    def deal_hand(self):
        """Deal new hand to each player and set card ownership."""
        for player in self.players:
            player.hand = [self.deck.deal_one()
                           for x in range(STARTING_HAND_SIZE)]
            
            for card in player.hand:
                card.owner = player.pNum
                
    def log(self, msg_type, msg):
        """Handle the game logging feature. Writes (XML?) to a specific file
        for each game.
        
        msg_type (??): Type of message, used to tag appropriately
        msg (string?): Content to write.
        """
        pass # A short method is an elegant method.

    def handle_card_played(self, player_num, card_num):
        """Invoke play processing logic on incoming play and send update to
        clients, or indicate illegal play to single player.

        player_num (int): local player number
        card_num (int): integer encoding of card being played by player

        """
        #check that player_num is active player
        
        ###########
        # Invoke play processing logic and return game state updates
        # to here. [We will use dicts for comm with router. JBG]
        # Game router will ensure message follows Comm Structure contract, so
        # formatting data here IAW those guidelines is optional but a good idea
        ###########

        if self.check_play_legality(self.players[player_num], card_num):
            # It's a legal play; do stuff here.
            self.gs.cards_in_play.append(self.players[player_num]
        else:
            return False # Not a legal play; return False
                         # Game router will chastise appropriately.
        
        #######
        # Based on earlier chats, this will return a list of dicts like:
        # [ {'target':0, ...data...}, {'target':1, ...data...}, ...]
        #  (change this as you like)
        # where ...data... will be whatever needs to be returned. Could be
        # expressed as {..., 'data':{...data dict...} } if easier.
        #
        # Can create one dict for each player. Identical messages for several
        # players can be consolidated by the game router.
        #
        # this should gather all info needed to describe the new game state.
        # do end-of-hand/tricks within play processing; the client will render
        # actions in the proper order, just by sending one message (i.e. don't
        # use separate messages for card play, end of trick, and new hand).
        #######

        return

    def start_game(self):
        """Start game."""
        self.create_players()
        self.deal_hand()
        #init scores?
        #what other pre-game things need to happen?

        data = []

        return data #need to return info to game_router containing init hands,
                # active player, etc. to send starting Messages. This will be
                # the same/similar info that is sent at start of each Hand.

#test
if __name__ == '__main__': 
    print("Creating new game with 4 players.")
    g = Game()
    g.start_game()
    print(g)
    print("Undealt cards:",g.deck)
    print("players[2].hand=",g.players[2].hand)
    g.gs = gs(42042)
    print(g.check_play_legality(g.players[2],g.players[2].hand[3].code))
    print(g.check_play_legality(g.players[2],34))
