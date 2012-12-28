#!/usr/bin/python3
"""Management system for Cinch AI Agents.

Will handle creation, maintanance, etc. for AI Agents. Will provide information
to engine/client for selecting from multiple AI models.

Does not perform game traffic routing. Agents will be (mostly) autonomous
clients, conducting game traffic through Comet server used by human players.
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

import logging
log = logging.getLogger(__name__)


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
        self.agents = [] # Activated (Agent, Pipe, Process) tuples
        
        #self.get_ai_models()
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
            parent_conn, agent_conn = multiprocessing.Pipe()
            agent = cls(agent_conn)
            p = multiprocessing.Process(target=agent.start,
                                        name=agent.identity['name'])
            log.debug("Thread created for model_num={0}".format(model_num))
            
            self.agents.append((agent, parent_conn, p))
            p.start() # Start multiprocessing.Process
            log.debug("Thread.start() ran for model_num={0}".format(model_num))
            
        except Exception:
            log.exception("Error creating agent")
            return None
            
        return parent_conn

    def create_agent_for_existing_game(self, model_num, game_id, pNum):
        """Create new agent and issue 'join game' command to it.

        model_num (int): index of desired agent in available agent models
        game_id (int): id of target game for new agent
        
        """
        pipe = self.create_agent(model_num)

        data = (2,game_id,pNum) # 2 = join game
        self.send_message(pipe, data)
        log.info("Agent with model_num={0} and pNum={1} created"
                 " for game {2}".format(model_num, pNum, game_id))

    def create_agent_for_new_game(self, model_num, plrs=None):
        """Create new agent and issue 'new game' command to it. Can only be
        invoked via command console.

        model_num (int): index of desired agent model in models[]

        """
        pipe = self.create_agent(model_num)
        data = (1,)
        self.send_message(pipe, data)
        log.info("Agent with model_num={0} creating new game".format(model_num))

        sleep(0.4) # Allow time for game to be created (suspected race cond.)
        
        if plrs is None: # AI Agent will be playing a mirror match
            plrs = "{0},{1},{2}".format(model_num,model_num,model_num)

        n = 1
        for p in plrs.split(","): # Spawn AI agents from plrs for games
            self.create_agent_for_existing_game(int(p), -1, n)
            n = n+1

    def send_message(self, pipe, msg):
        """Send specified message to agent via subprocess pipe.

        pipe (Pipe): agent info
        msg (tuple): message

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
        data = (-1,) # -1 = shutdown
        self.send_message(pipe, data)
