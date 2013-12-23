#!/usr/bin/python2
"""Base functionality for Cinch AI agents.

Method reference:

...

TODO:
    - have 'thinking' timeout value (halt thinking after certain interval)
    --- mandate a timeout; can be a Timer call to change a loop value & publish
    --- can specify timeout in this file? want all agent models equal in this
    --- To devs: don't publish an AI that takes forever to do anything!
    - if AI are allowed to use DB, impl methods here

"""
from socketIO_client import SocketIO, BaseNamespace


PORT = 8088  # Corresponds with socket.io port opened on server


class AINamespace(BaseNamespace):

    """Comms interface with socketIO server."""

    def __init__(self, *args):
        super(AINamespace, self).__init__(*args)

    def on_connect(self):
        print '[AI connected]' # TODO include agent ID


class AIBase:
    
    """Common features of all Cinch AI Agents."""
    
    def __init__(self, *args):
        # Establish socketIO connection
        self.socketIO = SocketIO('localhost', PORT)
        self.ns = self.socketIO.define(AINamespace, '/cinch')

    def __del__(self):
        """Safely shutdown AI agent."""
        self.ns.disconnect()

    # ===============
    # Game Rules
    # ===============

    pass

    # ===============
    # Intelligence
    # ===============

    def act(self):
        """Initiate intelligent action.

        This is to be implemented within each agent. ...

        """
        raise NotImplementedError("act() needs to be implemented in subclass.")


testAI = AIBase()
