#!/usr/bin/python2
"""
game engine
"""
import logging
import logging.config
import threading

import web.server
from ai.manager import AIManager

#from engine.client_manager import ClientManager
#from engine.game_router import GameRouter


class Cinch:
    def __init__(self):
        logging.config.fileConfig('logging.config')
        self.running = True

        # Start AI manager
        manager = threading.Thread(target=AIManager)
        manager.daemon = True
        manager.start()

        # Start server
        web.server.runServer() # This blocks until keyboard interrupt
        
        # Begin cleanup
        logging.info("Cleaning up...")
        self.running = False

# Command console will be implemented as a client with access to a different
# namespace. make use of an ACL and perform some authentication. Easy approach
# may be to check the IP of the commander against the server IP (only local
# processes should be commanding).

if __name__ == "__main__":
    Cinch()
