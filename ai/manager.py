#!/usr/bin/python3
"""Management system for Cinch AI Agents.

Will handle creation, maintanance, etc. for AI Agents. Will provide information
to engine/client for selecting from multiple AI models.

Does not perform game traffic routing. Agents will be (mostly) autonomous
clients, conducting game traffic through Comet server used by human players.
Manager can send instructions to agents to make them join games and shutdown.

...

- will create drop-down info for agent selector on client side
--- requires new message interface for client to create new games

--maybe register manager callback with game router to read all new-game
requests

TODO:
    - incorporate into game router
    --- create AI Manager at root level, attach to game router
    --- will need new 'new game/join game' handlers there to support game lobby
    - limit memory/cpu usage: do here so AI agents can't override
    --- unix can use `resource` module


Method reference:

class AIManager
-get_ai_models()
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

import logging
log = logging.getLogger(__name__)


# Constants
MAX_AGENTS = 20 #TODO: change this with respect to server resources


class AIManager:

    ####################
    # Manager Management
    ####################

    def __init__(self):
        self.agents = [] # Activated (Agent, Pipe, Process) tuples
        self.ai_packages = [] # Available AI models
        
        self.get_ai_models()
        log.info("AI Manager ready for action.")

    def cleanup(self):
        """Shut down all active agents."""
        for agent, pipe, proc in self.agents:
            log.info("Shutting down AI agent...")
            self.shutdown_agent(pipe)
            proc.join()
            
    def get_ai_models(self):
        """Scan AI folder for agent models and add to self.models."""
        log.info("Searching for AI packages...")
        # Get directory listing of ai folder        
        cur = sys.modules[__name__]

        ai_path = os.path.join(os.getcwd(), "ai") #currently in root

        self.ai_path = ai_path #store value for later use
        
        dirlist = os.listdir(ai_path)

        # Remove __pycache__ from candidate packages, if present
        try:    dirlist.remove('__pycache__')
        except: pass

        curDir = os.getcwd()
        os.chdir(ai_path) # Filtering needs to be performed from AI directory
        
        # Filter non-directories from dirlist
        packages = filter(os.path.isdir, dirlist)

        # Gather ID info and import each package
        for pkg in packages:
            d = {'pkg': pkg}
            t = "{0}_module".format(pkg)

            exec("import ai.{0} as {1}".format(pkg,t))
            self.ai_packages.append(locals()[t])
            log.info("Found AI Model {0}".format(
                        locals()[t].Agent.identity['name']))

        os.chdir(curDir) # Change to old working directory
        log.info("AI Model data loaded ({0} models).".format(
                    len(self.ai_packages)))

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

        #TODO: may want to sort ai_packages first, somehow
        for pkg in self.ai_packages:
            identity = pkg.Agent.identity
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
            pkg = self.ai_packages[model_num]
        except IndexError: # model_num out of range
            log.warning("model_num={0} out of range;"
                        " defaulting to model_num=0".format(model_num))
            model_num = 0
            pkg = self.ai_packages[0]

        agent, parent_conn = None, None
        try:
            parent_conn, agent_conn = multiprocessing.Pipe()
            agent = pkg.Agent(agent_conn)
            p = multiprocessing.Process(target=agent.start,
                                        name=pkg.__name__)
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
