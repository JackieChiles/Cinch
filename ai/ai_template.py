#!/usr/bin/python3
"""AI Template. Minimum stuff required to load properly."""

# Imports from library


# Import base class for AI agent
from ai.base import AIBase, log

AI_CLASS = "Classname" # Set this to match the class name for the agent
__author__  = "author"
__version__ = "version"
__date__    = "date"
__skill__   = "skill"
__agent_name__  = "name"
__description__ = "description"


class Classname(AIBase):
    def __init__(self, pipe):
        super().__init__(pipe, self.identity)  # Call to parent init

    def act(self):
        """Overriding base class act."""
        if self.pNum==self.gs.active_player:
            pass
