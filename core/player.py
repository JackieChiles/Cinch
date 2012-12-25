#!/usr/bin/python3
"""
Container class for player attributes.
"""
class Player:
    """
    Define Player object with instance variables:

    pNum (int): unique (within game) id for player object, set by Game object
    user_id (int): placeholder for user id/user account id
    name (string): display name of player
    hand (list): array of card objects, set by Game object
    """
    def __init__(self, pNum, name="test"):
        """
        Create new Player object.
        """
        self.pNum = pNum
        self.name = name  # Player name needs to be available to the Player
                          # object in order to write it to the log database.
        
        self.hand = []

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Player {0} with {1} cards in hand.".format(
                self.name, len(self.hand))

