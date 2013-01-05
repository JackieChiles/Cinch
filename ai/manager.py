#!/usr/bin/python3
"""Management system for Cinch AI Agents.

Will handle creation, maintanance, etc. for AI Agents. Will provide information
to engine/client for selecting from multiple AI models.

Does not perform game traffic routing. Agents will be (mostly) autonomous
clients, conducting game traffic directly to the game engine.
Manager can send instructions to agents to make them join games and shutdown.

Inspired in part by https://github.com/okayzed/dmangame

...

Method reference:

import_module(module_name)
get_ai_models()
set_ai_ident(module)

class AIManager
-get_ai_summary()
-create_agent(model_num)
-create_agent_for_new_game(model_num)
-create_agent_for_existing_game(model_num, game_id, pNum)
-send_message(agent, msg)
-shutdown_agent(agent_num)

"""
import multiprocessing
import sys
import os
import imp
from time import sleep
from _thread import start_new_thread # for monitoring queue

import logging
log = logging.getLogger(__name__)

from web.message import Message


# Constants
MAX_AGENTS = 20 #TODO: change this with respect to server resources

MY_PATH = os.path.abspath(os.path.dirname(__file__))
MODELS_FILE = "available_models.txt"


def import_module(module_name):
    """Import module from file and return module object.
    Copied (mostly) from docs.python.org.
    
    FUTURE: Rework this using the importlib library (requires Python 3.3+)
    
    module_name (string) - the name of the module (filename minus extention)
    """
    # In case something with module name is in global NS, remove it
    if module_name in sys.modules:
        del sys.modules[module_name]
    
    # Locate module within MY_PATH
    fp, pathname, desc = imp.find_module(module_name, [MY_PATH,])
    
    try:
        # Load it as though we had called 'import foo'
        return imp.load_module(module_name, fp, pathname, desc)
    finally:
        if fp:  fp.close()

def get_ai_models():
    """Read available models file for file names, and load corresponding
    classes into namespace.
    """
    # Open and parse models file
    log.info("Reading {0} for AI models...".format(MODELS_FILE))
    fin = open(os.path.join(MY_PATH, MODELS_FILE))
    
    ai_files = []
    line = fin.readline()
    while line:
        if line != '\n': # Ignore blank lines
            ai_files.append(line.strip()) # Remove trailing newline
        line = fin.readline()
    
    fin.close()
    
    # Import each file into a module
    ai_modules = []
    for filename in ai_files:
        split_ext = os.path.splitext(filename)            
        module_name = os.path.basename(split_ext[0])
        
        mod = import_module(module_name) # Create new module object
        ai_modules.append(mod)
        
        set_ai_ident(mod)  # Set identity of each AI class
        
        log.info("AI Agent {0} imported.".format(module_name))
 
    log.info("All available AI models imported.") 
    
    return list(map(lambda m: getattr(m, m.AI_CLASS), ai_modules))
    
def set_ai_ident(mod):
    """Set a self.identity for the AI class within mod."""
    cls = getattr(mod, mod.AI_CLASS)
    cls.identity = {  'author':   mod.__author__,
                      'version':  mod.__version__,
                      'date':     mod.__date__,
                      'skill':    mod.__skill__,
                      'name':     mod.__agent_name__,
                      'description':  mod.__description__
    }

class AIManager:
    # Placed here instead of in __init__ to play nice with multiprocessing
    ai_classes = get_ai_models()
    
    def __init__(self):
        self.gr = None # Game router reference, set during game router init
        self.agents = [] # Activated (Agent, Pipe, Process) tuples
        
        self.active_agents = {} # Reference for active agents, keyed by guid
        
        self.queue = multiprocessing.Queue()
        
        start_new_thread(self.listen_to_agents, ())
        
        log.info("AI Manager ready for action.")

    def cleanup(self):
        """Shut down all active agents."""
        for agent, pipe, proc in self.agents:
            log.info("Shutting down AI agent...")
            self.shutdown_agent(pipe)
            proc.join()

    def get_ai_summary(self):
        """Assemble data for choosing/viewing available AI Agents.

        Uses data contained in self.ai_packages to send to client. Client will
        use data to build AI Agent selection elements to be used when making
        new games. All data should be triple-underscored.

        Information will be requested by client using the 'ai' message flag.

        """
        aList = []
        temp = {}
        i = 1 # Used for AI ID #

        for ai_class in self.ai_classes:
            identity = ai_class.identity
            temp = {'id': i,
                    'auth': identity['author'],
                    'ver':  identity['version'],
                    'date': identity['date'],
                    'skl':  identity['skill'],
                    'name': identity['name'],
                    'desc': identity['description']
            }

            aList.append(temp)
            i += 1

        return aList
    
    def listen_to_agents(self):
        """Monitors self.queue for messages from Agents"""
        while True:
            msg = self.queue.get()
            uid = msg.pop('uid')

            # Do something with message (for now just send it to the game router)
            msg_sig = sorted(msg.keys())
            
            # Find appropriate handler
            for handler in self.gr.handlers:
                hand_sig = sorted(handler.signature)
                if msg_sig == sorted(handler.signature):
                    # Package msg as a Message object
                        message = Message(msg, source=uid)
                        handler.respond(message)
            

    ####################
    # Agent Management
    ####################

    def create_agent(self, model_num):
        """Spawn AI subprocess and store contact info.

        Returns subprocess (Popen) object for created agent, or None on error.

        model_num (int): index for ai model

        """
        if len(self.agents) > MAX_AGENTS:
            # Too many agents on the dance floor
            log.warning("MAX_AGENTS limit exceeded.")
            return None

        model_num = model_num - 1 # IDs sent to client start at 1, not 0

        # Select AI package
        try:
            cls = self.ai_classes[model_num]
        except IndexError: # model_num out of range
            log.warning("model_num={0} out of range;"
                        " defaulting to model_num=0".format(model_num))
            model_num = 0
            cls = self.ai_classes[0]

        agent, parent_conn = None, None
        try:
            # writing on parent_conn can be read from agent_conn
            parent_conn, agent_conn = multiprocessing.Pipe()
            agent = cls(agent_conn) # Pass pipe to Agent.init
            p = multiprocessing.Process(target=agent.start,
                                        args=((self.queue),),        # Pass queue to Agent.start()
                                        name=agent.identity['name']) # name = name of thread
            log.debug("Thread created for model_num={0}".format(model_num))
            
            self.agents.append((agent, parent_conn, p))
            
            p.start() # Start multiprocessing.Process
            log.debug("Thread.start() ran for model_num={0}".format(model_num))    
            return parent_conn
            
        except Exception:
            log.exception("Error creating agent")
            return None
           
    def create_agent_for_game(self, model_num, client_id, pNum):
        """Create agent for game. If game_id=None, then a new game is needed.
        
        model_num (int): index of desired agent in available agent models
        game_id (int/None): game to join
        pNum (int/None): desired player number
        
        """
        pipe = self.create_agent(model_num)

        # Add new agent to reference dict ###kind of redundant
        self.active_agents[client_id] = pipe
        
        # Pass player number to AI
        self.send_message(pipe, {'cmd': (1, client_id, pNum)})
        
        return "test"  ## this should be the name of the AI, formatted by pNum

    def send_message(self, pipe, msg):
        """Send specified message to agent via subprocess pipe.

        pipe (Pipe): agent info
        msg (dict): message

        """
        try:
            pipe.send(msg)
        except Exception:
            log.exception("Failed to send agent message '{0}' via pipe {1}."
                          "".format(msg, pipe))

    def shutdown_agent(self, pipe):
        """Issue shutdown command to agent.

        pipe (Pipe): Pipe connection to Agent

        """
        data = {'cmd': (-1,)} # -1 = shutdown
        self.send_message(pipe, data)


