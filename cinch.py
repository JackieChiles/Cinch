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

#listener registration
server.add_responder(chats, web.channel.CHAT_SIGNATURE)

#announcer regstration -- won't always do both on same object
# some things may only announce (eg daemons), while others only respond to
# client actions. but if an object wants any sort of multicast/broadcast
# ability, it must be registered as an announcer.
server.add_announcer("chat", chats)


#Start server
server.run_server()



#debug

