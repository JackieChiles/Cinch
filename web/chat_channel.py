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

    def attach_client_manager(self, cm):
        """Attach client manager from the game engine to Chat Engine.

        cm (ClientManager): Client Manager created at the root level

        """
        self.client_mgr = cm

    ## Overriden members.
    def register(self, server):
        """Register ChatEngine as announce and responder to the server.

        Add responder to listen for chat messages. No response will be sent.
        Use announce mode to multi-cast chat message to other parties in room.

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

        cm = self.client_mgr

        # Extract chat message from Message object
        chat = incoming_msg.data.get('msg', "")

        # Get GUIDs of clients in chat room
        group_id = cm.get_group_by_client(incoming_msg.source)
        recipients = cm.get_clients_in_group(group_id)

        # Package into Message and notify the server
        ##(??) uNum is the clients ID number within the chat room (cf. pNum)
        uNum = recipients.index(incoming_msg.source)
        msg_data = {'uNum':uNum, 'msg':chat}
        msg = Message(msg_data,
                      source=incoming_msg.source, dest_list=recipients)
        self.announce(msg)

        # No error conditions exist for chat, so return None
        return None
