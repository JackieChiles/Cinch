#!/usr/bin/python3
"""Base class for providing objects with interface to server.

rename to Channel
"""
#import signatures?
#CHAT_SIGNATURE = ['user', 'msg']
CHAT_SIGNATURE = ['message']

class CommChannel:
    """Provide interface functions for interacting with server. Intended
    to be subclassed by objects requiring Rx/Tx with Comet server.

    signature (list): list of JSON keys required for this to handle message
    callback (function): fun object for handling message -- rework this!!

    """
    def __init__(self, signature, callback):
        """

        """
        self.signature = signature
        self.callback = callback

    def web_announce(self):
        """

        """
        raise AssertionError("Must implement web_announce.")
    
    def web_listen(self):
        """

        """
        raise AssertionError("Must implement web_listen.")

    


###here for testing purposes; move to proper class file later
class Chats(CommChannel):
    """
    """
    def __init__(self):
        CommChannel.__init__(self, CHAT_SIGNATURE, self.handle_chat)

    def handle_chat(self, msg):
        """"""
        #return "CHATS", "chats received"
        return "CHAT", msg
        
    
