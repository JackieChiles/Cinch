#!/usr/bin/python2
"""
game engine
"""
import logging
import logging.config


import web.server

#from engine.client_manager import ClientManager
#from engine.game_router import GameRouter

#from ai.manager import AIManager


class Cinch:
    def __init__(self):
        logging.config.fileConfig('logging.config')
        self.running = True

        # Create services
       # self.client_mgr = ClientManager()
       # self.gr = GameRouter()
        ##self.chat_engine = ChatEngine()
        ##self.ai_mgr = AIManager()

        # Interconnect services
        #self.gr.attach_client_manager(self.client_mgr)
        ##self.gr.attach_ai_manager(self.ai_mgr)
        ##self.chat_engine.attach_client_manager(self.client_mgr)

        # Register services with web server
        #self.gr.register_handlers(self.server)
        #self.chat_engine.register(self.server)
        
        # Start server
        web.server.runServer() # This blocks until keyboard interrupt
        
        # Begin cleanup
        logging.info("Cleaning up...")
        self.running = False

        #self.ai_mgr.cleanup()

# Command console will be implemented as a client with access to a different
# namespace. make use of an ACL and perform some authentication. Easy approach
# may be to check the IP of the commander against the server IP (only local
# processes should be commanding).

# AIs may be well served with greenlets -- lightweight threads. Need to study
# up on that library. Planning to reimplement AI as stand-alone processes, using
# the socketio library to communicate with the server as regular clients. May
# consider leveraging an ACL to give AIs access to more resources, but probably
# not. Still need an AI manager in charge of exposing AI agents to engine and
# handling their creation -- maybe let them timeout via sockets and self-destruct.
        
if __name__ == "__main__":
    # Needed to keep Win32 systems from making bad things with multiprocesses
   # freeze_support() # not going to multiprocess AI anymore,

    Cinch()
