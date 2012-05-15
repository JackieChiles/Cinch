#!/usr/bin/python3
"""AI Agent demonstration of module implementation."""

# Import base class for AI agent -- TODO may need to edit import path
try:
    from ....base import AIBase
except:
    from base import AIBase


class DemoAgent(AIBase):
    def __init__(self):
        super().__init__()   # pref. way of calling parent init

        print("DemoAgent AI loaded")

    def act(self):
        """Overriding base class act."""
        print("DemoAgent acting...")
        pass

## Agent is initialized in __init__.py. You only need to define class objects
## and helper functions here.
