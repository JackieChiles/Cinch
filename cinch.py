#!/usr/bin/python3
"""
game engine
"""
import web.web_server
from web.chat_channel import ChatEngine

from engine.game_router import GameRouter

#Create server
server = web.web_server.boot_server()

gr = GameRouter()
gr.register_handlers(server)

def get_client_guids(guid):
    return gr.get_client_guids(guid)

#Register game objects with server
chat_engine = ChatEngine(get_client_guids)
chat_engine.register(server)

#Start server
server.run_server()

#debug

