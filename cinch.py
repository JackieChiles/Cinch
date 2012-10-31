#!/usr/bin/python3
"""
game engine
"""
import logging
import logging.config
from multiprocessing import freeze_support
from multiprocessing.connection import Client, Listener
from _thread import start_new_thread
from time import sleep

import web.web_server
from web.chat_channel import ChatEngine

from engine.client_manager import ClientManager
from engine.game_router import GameRouter

from ai.manager import AIManager


self_address = ('localhost', 8675)
commander_address = ('localhost', 8676)


class Cinch:
    def __init__(self):
        logging.config.fileConfig('logging.config')
        self.running = True
        
        # Start command interface listener
        start_new_thread(self.command_interface, ())
            
        # Create web server
        self.server = web.web_server.boot_server()

        # Create services
        self.client_mgr = ClientManager()
        self.gr = GameRouter()
        self.chat_engine = ChatEngine()
        self.ai_mgr = AIManager()

        # Interconnect services
        self.gr.attach_client_manager(self.client_mgr)
        self.gr.attach_ai_manager(self.ai_mgr)
        self.chat_engine.attach_client_manager(self.client_mgr)

        # Register services with web server
        self.gr.register_handlers(self.server)
        self.chat_engine.register(self.server)
        
        # Start server
        self.server.run_server() # This blocks until killed (usu. by Ctrl-C)
        
        # Begin cleanup
        logging.info("Cleaning up...")
        self.running = False

        self.ai_mgr.cleanup()

    def command_interface(self):
        """Listen on particular socket/port for commands and execute, returning
           output from their execution to appropriate listening port."""
        listener = Listener(self_address)

        while self.running: # Looping here allows for commanders to come & go
            conn_in = listener.accept() # Wait for incoming connection
            logging.debug("Commander's connection accepted from {0}"
                     "".format(listener.last_accepted))

            sleep(0.5) # Allow commander time to prepare
            conn_out = Client(commander_address)

            # Handle commands from commander's console
            while True:
                try:
                    msg = conn_in.recv()
                except EOFError: # Commander died
                    conn_in.close()
                    break

                # Handle msg here & gather response
                response = msg
                
                if 'help' == msg:
                    response = """Valid commands:
    ai x [y] - create AI-only game with players 
        x - agent model number
        y - 'plrs' string no quotes/spaces (e.g. "1,2,3"); if omitted, then
            AI plays self. ONLY use 3 items!
    help - show this message
    halt - stops Cinch server
    show games - get listing of all active games
"""

                elif 'ai' == msg[:2]:
                    cmd = msg.split()
                    
                    # Direct AI Manager to follow command
                    if len(cmd) == 3:
                        self.ai_mgr.create_agent_for_new_game(int(cmd[1]),
                                                              cmd[2])
                    else:
                        self.ai_mgr.create_agent_for_new_game(int(cmd[1]))

                elif 'halt' == msg:
                    self.server.shutdown()
                    response = "Cinch server shutdown."
                
                elif 'show games' == msg:
                    response = self.gr.games
                
                else:
                    response = "Unrecognized command. Try 'help' much?"
                
                # Send response back to commander
                conn_out.send(response)
            
            logging.debug("closing commander channel")
            
        conn_out.close()
        listener.close()
        
        
if __name__ == "__main__":
    # Needed to keep Win32 systems from making bad things with multiprocesses
    freeze_support()

    Cinch()
