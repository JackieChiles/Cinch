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
    def __init__(self, pNum, name="test", player_type=0): #Defaults for debug
        """
        Create new Player object.
        """
        self.pNum = pNum
        self.name = name  #Player name needs to be available to the Player
                          #object in order to write it to the log database.
        
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
