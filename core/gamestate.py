#!/usr/bin/python3

#import

#this allows game.py to be ran alone from core dir AND as part of cinch.py
# for development.
## once final, will use only absolute imports (core.*)
try:
    import common
    import cards
except ImportError:
    import core.common as common
    import core.cards as cards
    
# Constants; these can be replaced later
NUM_PLAYERS = 4
TEAM_SIZE = 2

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
    scores (list of integers): score for each team
    """

    def __init__(self, game_id):
        self['game_id'] = game_id
        self['trump'] = 0
        self['dealer'] = 0
        self['high_bid'] = 0
        self['declarer'] = 0
        self['active_player'] = 0
        self['cards_in_play'] = []
        self['scores'] = [0, 0]
        self['team_stacks'] = [[], []]
    
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
        for each in self['cards_in_play']:
            if each.suit == winning_suit:
                if each.rank > current_highest_card_rank:
                    current_highest_card_rank = each.rank
                    current_highest_card_owner = each.owner
        return current_highest_card_owner
        
    def score_hand(self):
        """Score a completed hand and adjust scores."""
        # Assumption is that teams are of equal size and seated alternately.
        # Code should work for any number of teams with any (equal) number of
        # players.
        # This method does not verify that the hand is actually over.
        
        # Initialize the comparison variables.
        current_high_rank = 0
        current_low_rank = 15
        current_best_game_point_total = 0
        game_points = [0]*TEAM_SIZE # Allows for arbitrary number of teams
        jack_holder = None # Jack not necessarily out
        game_holder = None # Game not necessarily out (ties)
        
        # team_number and *_holder are indices referencing a particular team.
        for team_number in range(len(self['team_stacks'])):
            for card in self['team_stacks'][team_number]:
                if card.suit == self['trump']:
                    if card.rank > current_high_rank:
                        current_high_rank = card.rank
                        high_holder = (card.owner % TEAM_SIZE)
                    if card.rank < current_low_rank:
                        current_low_rank = card.rank
                        low_holder = (card.owner % TEAM_SIZE)
                    if card.rank == 11:
                        jack_holder = team_number
                if card.rank > 10:
                    game_points[team_number] += (card.rank - 10)
                if card.rank == 10:
                    game_points[team_number] += card.rank
         
        # Determine who gets the Game point, no point for a tie.
        for team, team_total in list(enumerate(game_points)):
            if team_total > current_best_game_point_total:
                current_best_game_point_total = team_total
                game_holder = team
            else:
                if team_total == current_best_game_point_total:
                    game_holder = None
         
         
        # All cards accounted for, now assign temp points to teams.
        temp_points = [0, 0] # Initialize to be able to increment
        temp_points[high_holder] += 1
        temp_points[low_holder] += 1
        if jack_holder is not None:
            temp_points[jack_holder] += 1
        if game_holder is not None:
            temp_points[game_holder] += 1
         
        # Compare to bids and adjust scores.
         
        declaring_team = self['declarer'] % TEAM_SIZE
         
        # Handle cinching and getting set.
         
        if self['high_bid'] == 5: # Don't hardcode this, it's CINCH.
            if temp_points[declaring_team] == 4:       # Made it.
                if self['scores'][declaring_team] == 0:         # Auto-win.
                    temp_points[declaring_team] = 11
                else:
                    temp_points[declaring_team] = 10
            else:                                           # Ouch, set.
                temp_points[declaring_team] = -10
        else:
            if temp_points[declaring_team] < self['high_bid']: # Set
                temp_points[declaring_team] = -1*self['high_bid']
         
        for each in range(len(self['scores'])):
            self['scores'][each] += temp_points[each]
            
        return None
        
if __name__ == "__main__":
    print("Default Game State")
    gs = GameState(2000)
    gs['trump'] = 1
    gs['dealer'] = 2
    gs['high_bid'] = 5
    gs['declarer'] = 0
    d = cards.Deck()
    for x in range(36):
        gs['team_stacks'][x%2].append(d.deal_one())
        gs['team_stacks'][x%2][-1].owner = x % NUM_PLAYERS
    print(gs['team_stacks'])
    gs.score_hand()
    print(gs['scores'])


        
        
