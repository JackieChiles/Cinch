#!/usr/bin/python3
"""

"""
#import


#may want better way of doing this
HUMAN = 0
COMPUTER = 1


class Player:
    """
    Define Player object with instance variables:

    pNum (int): unique (within game) id for player object, set by Game object
    user_id (int): placeholder for user id/user account id
    name (string): display name of player
    hand (list): array of card objects, set by Game object
    has_last_state (boolean): does client have latest game state, set by Game
    """
    def __init__(self, pNum, game_id=0, name="test",
                 player_type=0):   #set defaults for debugging
        """
        Create new Player object.
        """
        self.pNum = pNum
        
        self.game_id = game_id  #may not be needed
        self.name = name  #player name currently lives in client manager;
                          #do we need it here? (logging info??)
        
        self.hand = None

        if player_type == HUMAN:
            pass
            #Do things to make human player; maybe new class

        elif player_type == COMPUTER:
            pass
            #Do things to make AI player; maybe new class

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Player {0} with {1} cards in hand.".format(self.name,
                                                           len(self.hand))

    
        
if __name__ == '__main__':
    p = Player()
    print(p)
    #test code
