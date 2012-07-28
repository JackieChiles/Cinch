#!/usr/bin/python3

####################
# Edit this information for your AI Agent implementation
####################

# Enter the class name specified in core.py for your AI Agent
agent_classname = "Rand"

# AI Agent description -- used by Manager for identification
## starts with triple-underline
___author  = "JACK!"
___version = "1.0"
___date    = "8 July 2012"
___skill   = "0"
___agent_name  = "Rand"
___description = "Pseudo randomness at its best."


####################
# Don't edit infomation below this line (unless you need to)
####################

exec("from .core import {0} as Agent".format(agent_classname))

# Make the agent's identity easily available to itself.
Agent.identity = {  'author':   ___author,
                    'version':  ___version,
                    'date':     ___date,
                    'skill':    ___skill,
                    'name':     ___agent_name,
                    'description':  ___description
                 }


