#!/usr/bin/python3
"""A driver utility to test stuff in the cinch game engine."""

import argparse
import logging
import core.game

log = logging.getLogger(__name__)
LOG_SHORT = {'d':'DEBUG',
             'i':'INFO',
             'w':'WARNING',
             'e':'ERROR',
             'c':'CRITICAL'}

def main(option):
    if option:
        for x in range(2): # Simulate 2 games in a row like this.
            g = core.game.Game(True, 0.35)
            g.start_game()
            log.debug('first game id - %s',g.gs.game_id)
            for player in g.players:
                log.debug('%s\'s hand: %s', player.name, player.hand)
            for _ in range(4):
                if g.players[g.gs.active_player].name == "Test1":
                    g.handle_bid(g.gs.active_player, 5)
                else:
                    g.handle_bid(g.gs.active_player, 0)
            log.debug("Bidding over. Active player is:")
            log.debug("%s with %s", g.players[g.gs.active_player].name,
                      g.players[g.gs.active_player].hand)
    
            log.debug("Playing some cards...")
            play_order = [52,46,48,49, 25,19,22,14, 37,33,34,32, 35,28,29,27,
                           2, 7, 9, 1, 42,47,40,45, 13, 8, 3,10, 20,15, 6,16,
                          44,23,41,21]
            for card_code in play_order:
                g.handle_card_played(g.gs.active_player, card_code)
    
            log.debug("Cards remaining in hands:")
            for player in g.players:
                log.debug('%s\'s hand: %s', player.name, player.hand)
            log.debug("Active player is %s", g.players[g.gs.active_player].name)

    else:
        log.error('No option specified, not doing anything.')
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description =
                                     'Test driver for cinch game engine.')
    parser.add_argument("-l", "--loglevel",
                        help="set log level (default=WARNING)", type=str,
                        choices = list(LOG_SHORT.keys()), default='w')
    parser.add_argument("-cr", "--chinese-room", action = 'store_true',
                        help="db lock testing: play 2 stacked games.")
    args = parser.parse_args()
    logging.basicConfig(level = LOG_SHORT[args.loglevel])

    main(args.chinese_room)
