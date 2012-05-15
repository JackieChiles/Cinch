#!/usr/bin/python3

####################
# Edit this information for your AI Agent implementation
####################

# Enter the class name specified in core.py for your AI Agent
agent_classname = "DemoAgent"

# AI Agent description -- used by Manager for identification
## starts with triple-underline
___author  = "author"
___version = "0.0.1"
___date    = "03 March 2012"
___skill   = "agent skill"
___agent_name  = "agent name"
___description = "Demo agent description."


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
