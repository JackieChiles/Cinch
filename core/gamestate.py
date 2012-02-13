#!/usr/bin/python3

#import
import common
import cards

# Constants; these can be replaced later
NUM_PLAYERS = 4

class GameState(dict):
    """
    Define object for GameState with class variables:
    
    This is the public information about the associated Game.
    Basic information is stored as key:value pairs.
    Derived information can be retrieved through the defined methods.
    
    
    game_id (int): id for corresponding game
    trump (int): current trump via Suits enum
    dealer (int, 0-3): local player id of player that dealt hand
    high_bid (int, 0-5): high bid on hand (5=Cinch)
    declarer (int, 0-3): local player id of player that made high bid
    active_player (int, 0-3): local player id of active player
    cards_in_play (list): list of card objects for cards in play
    scores (tuple, 2 integers): score for players 0&2 and 1&3
    """

    def __init__(self, game_id):
        self['game_id'] = game_id
        self['trump'] = 0
        self['dealer'] = 0
        self['high_bid'] = 0
        self['declarer'] = 0
        self['active_player'] = 0
        self['cards_in_play'] = []
        self['scores'] = (0, 0)
        self['past_tricks'] = [[], []]
    
    def next_player(self):
        """Move around the table one seat to the left."""
        self['active_player'] = (self['active_player'] + 1) % NUM_PLAYERS
        return None
        
    def suit_led(self):
        """Return the suit of the first card led this trick."""
        return self['cards_in_play'][0].suit
        
    def trump_played(self):
        """Return True if at least one member of cards_in_play
        is the current trump suit."""
        for each in self['cards_in_play']:
            if each.suit == self['trump']:
                return True
        return False
        
    def trick_winner(self):
        """Return the local player ID of the winner of the current trick.
        Return None if not enough cards in play."""
        
        # Make sure correct number of cards are in play.
        if len(self['cards_in_play']) != NUM_PLAYERS:
            return None
            
        # Determine which suit wins the trick.
        if self.trump_played():
            winning_suit = self['trump']
        else:
            winning_suit = self.suit_led()
        
        # Find the winning card and determine who played it.
        current_highest_card_rank = 0
        current_highest_card_pos = -1
        for each in self['cards_in_play']:
            if each.suit == winning_suit:
                if each.rank > current_highest_card_rank:
                    current_highest_card_rank = each.rank
                    current_highest_card_pos = self['cards_in_play'].index(each)
        return (self['active_player'] + current_highest_card_pos) % NUM_PLAYERS
        
    def score_hand(self):
        """Score a completed hand and adjust scores."""
        pass # Might need to tweak this code later. Doesn't seem to do much. >_>
         
        
if __name__ == "__main__":
    print("Default Game State")
    gs = GameState(2000)
    d = cards.Deck()
    for x in [1]*4:
        gs['cards_in_play'].append(d.deal_one())
    print(gs['cards_in_play'])
    print(gs.trick_winner())


        
        
