#!/usr/bin/python3
"""
game engine
"""
import web.web_server
import web.channel

#Create server
server = web.web_server.boot_server()


#Register game objects with server
##create chats object
chats = web.channel.Chats()
server.add_listener(chats)


#Start server
server.run_server()
