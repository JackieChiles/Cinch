#!/usr/bin/python3
"""
game engine
"""
import web.web_server
from web.chat_channel import ChatEngine

from engine.client_manager import ClientManager
from engine.game_router import GameRouter

# Create web server
server = web.web_server.boot_server()

# Create services
client_mgr = ClientManager()
gr = GameRouter()
chat_engine = ChatEngine()

# Interconnect services
gr.attach_client_manager(client_mgr)
chat_engine.attach_client_manager(client_mgr)

# Register services with web server
gr.register_handlers(server)
chat_engine.register(server)

# Start server
server.run_server()

#debug

