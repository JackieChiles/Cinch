#!/usr/bin/python2
"""Game engine."""


import logging
import logging.config

import threading
import argparse

import common
import web.server
from ai.manager import AIManager


if __name__ == "__main__":
    logging.config.fileConfig('logging.config')

    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", help="make game go quicker",
                        action="store_true")
    parser.add_argument("--stack", help="stack deck using given RNG seed",
                        type=float)
    args = parser.parse_args()

    if args.quick:
        logging.info("Quick game mode enabled")
        # These changes will be seen by web.server
        import core.game
        core.game.STARTING_HAND_SIZE = 2
        core.game.MAX_HANDS = 1

    if args.stack:
        logging.info("Deck stacking on for all games (seed = {0})".format(
            args.stack))
        import core.cards
        core.cards.STACK_DECK = True
        core.cards.DECK_SEED = args.stack

    # Start AI manager
    manager = threading.Thread(target=AIManager)
    manager.daemon = True
    manager.start()

    # Start server
    web.server.runServer() # Blocks

    # Begin cleanup
    logging.info("Cleaning up...")
