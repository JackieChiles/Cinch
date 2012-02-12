#!/usr/bin/python3
"""
game engine
"""
import web.web_server
from web.chat_channel import ChatEngine

from engine.game_router import GameRouter

#Create server
server = web.web_server.boot_server()

#Register game objects with server
chat_engine = ChatEngine()
chat_engine.register(server)

#Start server
#server.run_server()

gr = GameRouter()
gr.register_handlers(server)



#debug

