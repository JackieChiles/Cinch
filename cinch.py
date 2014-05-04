#!/usr/bin/python2
"""
Game engine.

"""
import logging
import logging.config

import threading
import argparse

import web.server
from ai.manager import AIManager


if __name__ == "__main__":
    logging.config.fileConfig('logging.config')

    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", help="make game go quicker", action="store_true")
    args = parser.parse_args()

    if args.quick:
        logging.info("Quick game mode enabled")
        # Preempt web.server's import of core.game to make changes
        import core.game
        core.game.STARTING_HAND_SIZE = 2
        core.game.MAX_HANDS = 1

    # Start AI manager
    manager = threading.Thread(target=AIManager)
    manager.daemon = True
    manager.start()

    # Start server
    web.server.runServer() # Blocks
    
    # Begin cleanup
    logging.info("Cleaning up...")
