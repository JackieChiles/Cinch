#!/usr/bin/python3
"""Base class for providing objects with interface to server.


"""
import json
from threading import Lock, Timer #might not need these

#CHAT_SIGNATURE = ['user', 'msg']
CHAT_SIGNATURE = ['message']


class CommChannel:
    """Provide interface functions for interacting with server. Intended
    to be subclassed by objects requiring Rx/Tx with Comet server.

    """
    def __init__(self):
        """Initialize CommChannel."""
        self.callbacks = dict() # will have 'announce' and 'respond' keys

        self.lock = Lock()  #might not need this

    def add_announce_callback(self, fun):
        """Adds callback to CommChannel for contacting server.

        Called by server on CommChannel object (server.add_announcer()).

        fun (function): notification function on server

        """
        assert callable(fun)

        self.callbacks['announce'] = fun

    def announce(self, msg):
        """Send broadcast-like message to web server.

        Classes that extend CommChannel will call this to send data (dicts)
        to the server. Message header is set during announcer registration.

        msg (dict): message to be announced
        
        """
        assert isinstance(msg, dict)

        f = self.callbacks['announce']
        f(msg)

    def respond(self, msg):
        """Read and respond to message from server.

        Must be implemented by each class that extends CommChannel.

        This is called by the server (server.handle_msg()).

        The response from here will be sent only to the client whose request
        triggered this response. Any broadcast-like messages must be sent
        through announce().

        msg (dict): incoming message from server
        returns: outgoing message to server

        """
        raise NotImplementedError("Must implement respond().")   


###here for testing purposes; move to proper class file later
class Chats(CommChannel):
    """Simple channel demonstration."""
    def __init__(self):
        CommChannel.__init__(self)

        #### debug
        t = Timer(3.0, self.announce, args=[{'msg':"announcement!"}])
        t.start()

    ## Overriden member
    def respond(self, args):
        """Overriding respond() from CommChannel.

        Demonstrating division between announcing and responding.
        """
        self.announce({'announce':args})
        return json.dumps(args)
        
    
