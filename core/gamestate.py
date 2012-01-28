#!/usr/bin/python3

#import


class GameState:
    """
    Define object for GameState with class variables:
    
    game_id (int): id for corresponding game
    id (int): unique id for game state object
    trump (int): current trump via Suits enum
    dealer (int, 0-3): local player id of player that dealt hand
    high_bid (int, 1-5): high bid on hand (5=Cinch)
    bid_winner (int, 0-3): local player id of player that made high bid
    active_player (int, 0-3): local player id of active player
    cards_in_play (array): array of card objects for cards in play
    scores (tuple, 2 integers): score for players 0&2 and 1&3
    (?)suit_led (int): just do self.cards[0].suit for example
    """

    def __init__(self, game_id):
        self.game_id = game_id
        self.id = 0
        
