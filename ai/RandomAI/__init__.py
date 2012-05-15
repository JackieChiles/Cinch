#!/usr/bin/python3

####################
# Edit this information for your AI Agent implementation
####################

# Enter the class name specified in core.py for your AI Agent
agent_classname = "RandomAgent"

# AI Agent description -- used by Manager for identification
## starts with triple-underline
___author  = "M.G."
___version = "1.0"
___date    = "17 March 2012"
___skill   = "0"
___agent_name  = "Random Agent"
___description = "Makes random bids and plays."


####################
# Don't edit infomation below this line (unless you need to)
####################

exec("from .core import {0} as Agent".format(agent_classname))

# Implement Agent's identification function -- TODO: does this add value?
def ident_self(self):
    return {'author':   ___author,
            'version':  ___version,
            'date':     ___date,
            'skill':    ___skill,
            'name':     ___agent_name,
            'description':  ___description
           }
Agent.identify_self = ident_self

agent = Agent()
agent.start()
