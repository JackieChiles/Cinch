#!/usr/bin/python3
"""
game engine
"""
from multiprocessing import freeze_support

import web.web_server
from web.chat_channel import ChatEngine

from engine.client_manager import ClientManager
from engine.game_router import GameRouter

from ai.manager import AIManager

if __name__ == "__main__":
    # Needed to keep Win32 systems from making bad things with multiprocesses
    freeze_support()
    
    # Create web server
    server = web.web_server.boot_server()

    # Create services
    client_mgr = ClientManager()
    gr = GameRouter()
    chat_engine = ChatEngine()
    ai_mgr = AIManager()

    # Interconnect services
    gr.attach_client_manager(client_mgr)
    gr.attach_ai_manager(ai_mgr)
    chat_engine.attach_client_manager(client_mgr)

    # Register services with web server
    gr.register_handlers(server)
    chat_engine.register(server)

    # Start server
    server.run_server() # This blocks until killed (usu. by Ctrl-C)

    # Begin cleanup
    print("Cleaning up...")

    ai_mgr.cleanup()
