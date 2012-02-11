#!/usr/bin/python3
"""Base class for providing communications objects for interfacing
with web server.

Classes that extend CommChannel must call CommChannel.__init__(self).
Classes that extend CommChannel must implement respond().

-Register a response channel with the web server:
    server.add_responder(channel_object, channel_signature)
channel_object: initialized object that extends CommChannel
channel_signature: list of dict keys for type of message channel_object will
    handle. Do NOT include the client GUID field -- that is broken out
    in Message object init.

-Register an announcement channel with the web server:
    server.add_announcer(channel_object)

One channel_object can perform one or both functions.

"""
import json

from web.message import Message


class CommChannel:
    """Provide interface functions for interacting with server. Intended
    to be subclassed by objects requiring Rx/Tx with Comet server.

    """
    def __init__(self):
        """Initialize CommChannel."""
        self.callbacks = dict() # will have 'announce' and 'respond' keys

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

        msg (Message): message to be announced
        
        """
        assert isinstance(msg, Message)

        f = self.callbacks['announce']
        f(msg)

    def register(self, server):
        """Register this comm channel with the web server.

        Must be implemented by each class that extends CommChannel.

        This is to be called from where the server is created, after
        booting the server but prior to running it.

        Specify server modes (announce and/or respond) and parameters when
        implementing this function.

        server: CometServer object

        """
        raise NotImplementedError("Must implement register().")

    def respond(self, msg):
        """Read and respond to message from server.

        Must be implemented by each class that extends CommChannel.

        This is called by the server (server.handle_msg()).

        The response from here will be sent only to the client whose request
        triggered this response. Any broadcast-like messages must be sent
        through announce().

        msg (Message): incoming message from server
        returns: outgoing Message object to server

        """
        raise NotImplementedError("Must implement respond().")
