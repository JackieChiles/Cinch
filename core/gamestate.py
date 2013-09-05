#!/usr/bin/python3
import core.common as common
import core.cards as cards

import logging
log = logging.getLogger(__name__)

   
# Constants; these can be replaced later
NUM_TEAMS = 2
TEAM_SIZE = 2
NUM_PLAYERS = NUM_TEAMS * TEAM_SIZE


class GameState:
    """
    Define object for GameState with class variables:
    
    This is the public information about the associated Game.
    Basic information is stored as key:value pairs.
    Derived information can be retrieved through the defined methods.
    
    
    game_id (str): id for corresponding game
    trump (int): current trump via Suits enum
    dealer (int, 0-3): local player id of player that dealt hand
    high_bid (int, 0-5): high bid on hand (5=Cinch)
    declarer (int, 0-3): local player id of player that made high bid
    active_player (int, 0-3): local player id of active player
    cards_in_play (list): list of Card objects for cards in play
    scores (list of integers): score for each team
    team_stacks (list of lists of Card objects): Cards taken this hand
    events (list): every output published, stored for db writes
    """
    def __init__(self, game_id):
        self.game_id = game_id
        self.game_mode = 2 # Change this later to MODE BID or whatever.
        self.trump = None
        self.dealer = 0
        self.high_bid = 0
        self.declarer = 0
        self.active_player = 0
        self.cards_in_play = []
        self.scores = [0]*NUM_TEAMS
        self.team_stacks = [[] for _ in range(NUM_TEAMS)]
        self.winner = 0.5 # Halfway between Team 0 and 1. Crafty, I know.
        # Count hands for logging/data collection and also to end the game
        # after some MAX_HANDS (intended to rein in AI deadlocks).
        # This starts at 1, and gets incremented in publish().
        self.hand_number = 1
        self.events = []
        
        # Journalist's variables to publish().
        self._t_w_card = None
        self._results = None
        self.countercinch = False
        
    def __repr__(self):
        """Print function for gamestate."""
        out = "Game # {0}\t\tMode: {1}\t\tTrump: {2}\n".format(self.game_id, self.game_mode, self.trump)
        out += "Dealer: {0}\t\tHigh bid: {1}\t\tDeclarer: {2}\n".format(self.dealer, self.high_bid, self.declarer)
        out += "Active Plr: {0}\t\tScores: {1}\n".format(self.active_player, str(self.scores))
        out += "Cards in play: {0}\n".format(self.cards_in_play)
        return out
    
    def next_player(self, player_num):
        """Return the player number of the player on the left of player_num."""
        return (player_num + 1) % NUM_PLAYERS
        
    def suit_led(self):
        """Return the suit of the first card led this trick."""
        return self.cards_in_play[0].suit
        
    def trump_played(self):
        """Return True if at least one member of cards_in_play
        is the current trump suit."""
        for each in self.cards_in_play:
            if each.suit == self.trump:
                return True
        return False
        
    def trick_winning_card(self):
        """Return the Card object that won the current trick.
        Return None if not enough cards in play."""
        
        # Make sure correct number of cards are in play.
        if len(self.cards_in_play) != NUM_PLAYERS:
            return None
            
        # Determine which suit wins the trick.
        if self.trump_played():
            winning_suit = self.trump
        else:
            winning_suit = self.suit_led()
        
        # Find the winning card and determine who played it.
        current_highest_card_rank = 0
        for each in self.cards_in_play:
            if each.suit == winning_suit:
                if each.rank > current_highest_card_rank:
                    current_highest_card_rank = each.rank
                    current_highest_card = each
        self._t_w_card = current_highest_card # For logging purposes.
        return current_highest_card
        
    def score_hand(self):
        """Score a completed hand and adjust scores.
        Assumption is that teams are of equal size and seated alternately.
        Code should work for any number of teams with any (equal) number of
        players.
        This method does not verify that the hand is actually over.
        
        return list of score changes for this hand, to be used for logging.
        """
        
        # Initialize the comparison variables.
        current_high_rank = 0
        current_low_rank = 15
        current_best_game_point_total = 0
        game_points = [0]*NUM_TEAMS # Allows for arbitrary number of teams
        jack_holder = None # Jack not necessarily out
        game_holder = None # Game not necessarily out (ties)
        declarer_set = False
        
        # team_number and *_holder are indices referencing a particular team.
        for team_number in range(len(self.team_stacks)):
            for card in self.team_stacks[team_number]:
                if card.suit == self.trump:
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
        temp_points = [0]*TEAM_SIZE # Initialize to be able to increment
        temp_points[high_holder] += 1
        temp_points[low_holder] += 1
        if jack_holder is not None:
            temp_points[jack_holder] += 1
        if game_holder is not None:
            temp_points[game_holder] += 1
         
        # Compare to bids and adjust scores.         
        declaring_team = self.declarer % TEAM_SIZE
         
        # Handle cinching and getting set.         
        if self.high_bid == 5: # Don't hardcode this, it's CINCH.
            if temp_points[declaring_team] == 4:         # Made it.
                if self.scores[declaring_team] == 0:     # Auto-win.
                    temp_points[declaring_team] = 11
                else:
                    temp_points[declaring_team] = 10
            else:                                        # Ouch, set.
                temp_points[declaring_team] = -10
                declarer_set = True
        else:
            if temp_points[declaring_team] < self.high_bid: # Set
                temp_points[declaring_team] = -1*self.high_bid
                declarer_set = True
         
        for each in range(len(self.scores)):
            self.scores[each] += temp_points[each]
            
        self._results = dict(high_holder = high_holder,
                            low_holder = low_holder,
                            jack_holder = jack_holder,
                            game_holder = game_holder,
                            declarer_set = declarer_set,
                            game_points = game_points)
        return

        
if __name__ == "__main__":
    log.warning("Are your cats old enough to learn about Jesus?")  
