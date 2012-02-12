#!/usr/bin/python3
"""Chat engine using CommChannel class."""
import web.web_config as config
from web.channel import CommChannel
from web.message import Message # for assertion

CHAT_SIGNATURE = ['msg']


class ChatEngine(CommChannel):
    """Chat engine implementation."""
    def __init__(self):
        CommChannel.__init__(self)

    ## Overriden members.
    def register(self, server):
        """Register ChatEngine as announce and responder to the server.

        Use announce mode to multi-cast chat message to other parties in room.

        Use respond mode to acknowledge receipt of message and order client to
        self-publish message (??? is this desirable???)

        """
        server.add_responder(self, CHAT_SIGNATURE)
        server.add_announcer(self)        

    def respond(self, incoming_msg):
        """Handle incoming chat message.

        Package chat message into Message with other game members
        as recipients.

        incoming_msg (Message): chat message with source and msg data
        
        """
        assert isinstance(incoming_msg, Message)

        # Extract chat message from Message object
        chat = incoming_msg.data.get('msg', "")

        # Get GUIDs of clients in chat room
        ##contact game router using incoming_msg.source to get
        ## need internal reference to game router, or means of
        ## registering channels to the router a la web server
        ### should return list
        recipients = [incoming_msg.source] #for testing purposes

        # Package into Message and notify the server
        msg_data = {'uNum':999, 'msg':chat}
        msg = Message(msg_data,
                      source=incoming_msg.source, dest_list=recipients)
        self.announce(msg)

        # No error conditions exist for chat, so return None
        return None
