#!/usr/bin/python3
"""
game engine
"""
import web.web_server
from web.chat_channel import ChatEngine

#Create server
server = web.web_server.boot_server()


#Register game objects with server
chat_engine = ChatEngine()
chat_engine.register(server)


#Start server
server.run_server()



#debug

