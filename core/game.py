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
    from gamestate import GameState
except ImportError:
    import core.common as common
    from core.player import Player
    import core.cards as cards
    from core.gamestate import GameState    

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
        return True # Couldn't follow suit, throwing off.
        
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
        
        Game router will ensure message follows Comm Structure contract, so
        formatting data here IAW those guidelines is optional but a good idea.
        
        player_num (int): local player number
        card_num (int): integer encoding of card being played by player

        """
        # Check that player_num is active player.
        if player_num is not self.gs.active_player:
            print("Non-active player attempted to play a card.") # Debugging
            return None # Ignore

        if not (self.check_play_legality(self.players[player_num], card_num)):
            return False # Not a legal play; return False
                         # Game router will chastise appropriately.
                         
        # Remove card from player's hand and put into play.
        for card_pos, card in list(enumerate(self.players[player_num].hand)):
            if card.code == card_num:
                if self.gs.trump is None: # First card played this hand?
                    self.gs.trump = card.suit
                    #TODO log Trump is:
                a = self.players[player_num].hand.pop(card_pos)
                self.gs.cards_in_play.append(a)
                #TODO self.log(Played a card.) Also message stuff.
                
        # End of trick logic
        tw = self.gs.trick_winner()
        if tw == None:
            # Trick is not over
            self.gs.active_player = self.gs.next_player(self.gs.active_player)
            #TODO message next player blah blah blah
            return
        self.gs.active_player = tw
        for each in range(len(self.gs.cards_in_play)):
            self.gs.team_stacks[tw % TEAM_SIZE].append(
                                    self.gs.cards_in_play.pop())

        # This is error checking to verify that all players have equal hand
        # sizes. Later, we can just check players[0].hand for cards.
        cards_left = 0
        for player in self.players:
            cards_left += len(player.hand)
        if cards_left % NUM_PLAYERS != 0:
            raise RuntimeError("Cards in hand not even.")
        if cards_left != 0:
            # More tricks to play
            #TODO message new active player
            return

        # End of hand logic
        self.gs.score_hand()
        #TODO message hand results
        victor = False
        for score in self.gs.scores:
            if score >= 11:
                victor = True
                break
        
        # This block breaks if there are more than two teams.        
        if victor:
            if score[self.gs.declarer % TEAM_SIZE] >= 11:
                #TODO log/message: declarer wins, final scores
                pass
            else:
                #TODO log/message: other team wins, final scores
                pass
            return
                
        # If no victor, set up for next hand.
        for stack in self.gs.team_stacks:
            stack = []
        self.gs.dealer = self.gs.next_player(self.gs.dealer)
        self.deck = cards.Deck()
        self.deal_hand()
        self.gs.active_player = self.gs.next_player(self.gs.dealer)
        self.gs.game_mode = GAME_MODE.BID
        self.gs.trump = None
        #TODO log/message: new hands, dealer, active player, game mode
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
    g.gs = GameState(42042)
    print("trump =",g.gs.trump)
    for x in range(8):
        for ii in range(4):
            g.players[ii].hand.pop()
    for x in range(3):
        g.gs.cards_in_play.append(g.players[x].hand.pop())
        print(g.gs.cards_in_play)
    print("players[3].hand=",g.players[3].hand)
    g.gs.active_player = 3
    g.handle_card_played(3, g.players[3].hand[0].code)
    print(g.gs.team_stacks)
