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
    --- consider moving manager.py to /engine/ (will need to tweak code)
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
import subprocess
import sys
import os

# Constants
MAX_AGENTS = 8 #TODO: change this with respect to server resources


class AIManager:

    ####################
    # Manager Management
    ####################

    def __init__(self):
        self.agents = [] # Activated AI agents
        self.ai_packages = [] # Available AI models
        
        self.get_ai_models()

        # Set path to python executable for create_agent()
        global python_path
        if "win" in sys.platform: # Running on Windows
            python_path = sys.executable
        else: # Running on UNIX, can use #!
            python_path = "/usr/bin/python3"
            
    def get_ai_models(self):
        """Scan AI folder for agent models and add to self.models."""
        # Get directory listing of ai folder        
        cur = sys.modules[__name__]

        #TODO: make correct one for final impl
        ai_path = os.getcwd()
        if ai_path[-2:] == "ai": #currently in AI directory
            pass
        else:
            ai_path = os.path.join(ai_path, "ai") #currently in root
        
        dirlist = os.listdir(ai_path)
        
        # Remove __pycache__ and _demo from candidate packages, if present
        try:    dirlist.remove('__pycache__')
        except: pass
        #try:    dirlist.remove('_demo') #TODO debug uncomment 
        #except: pass
        
        # Filter non-directories from dirlist
        packages = filter(os.path.isdir, dirlist)
        
        # Gather ID info from each package (___things from __init__.py)
        for pkg in packages:
            d = {'pkg': pkg}
            # Read pgk/__init__.py for triple-underscored values;
            # these are ID values
            p = os.path.join(ai_path, pkg, "__init__.py")
            with open(p, mode='r') as fp:
                for line in iter(fp.readline, ''):
                    if line[:3] == "___":
                        exec(line, globals(), d) # add line to d
            self.ai_packages.append(d)

    def get_ai_summary(self):
        """Assemble data for choosing/viewing available AI Agents.

        Uses data contained in self.ai_packages to send to client. Client will
        use data to build AI Agent selection elements to be used when making
        new games.

        Information will be requested by client via POST. Will likely want to
        register handler (a la CommChannel) and signature in order to get
        request directly; registration is done at the root level.

        """
        #TODO: update IAW game lobby specs
        raise NotImplementedError("Implementation pending decision on how/what the client will request.")

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
            return None #TODO will need to handle this in a useful way

        # Select AI package
        try:
            pkg = self.ai_packages[model_num]['pkg']
        except:
            # model_num out of range
            print("create_agent: invalid model_num", model_num)
            raise

        # Spawn subprocess (uses global python_path set in __init__())
        try:
            agent = subprocess.Popen([python_path, '-m', pkg], shell=False,
                                     stdin=subprocess.PIPE)
            self.agents.append(agent)          
        except OSError: # pkg doesn't exist
            agent = None
        finally:
            return agent

    #TODO: revise these methods after game lobby implemented
    def create_agent_for_existing_game(self, model_num, game_id, pNum):
        """Create new agent and issue 'join game' command to it.

        model_num (int): index of desired agent in available agent models
        game_id (int): id of target game for new agent
        
        """
        agent = self.create_agent(model_num)

        data = "2|{0}|{1}".format(game_id, pNum) # 2 = join game

        # Issue 'join game' command -- arguments are pipe delimited
        self.send_message(agent, data)    

    def create_agent_for_new_game(self, model_num):
        """Create new agent and issue 'new game' command to it.

        model_num (int): index of desired agent model in models[]

        """
        agent = self.create_agent(model_num)

        data = "1" # 1 = new game

        # Issue 'new game' command
        self.send_message(agent, data)

    def send_message(self, agent, msg):
        """Send specified message to agent via subprocess pipe.

        agent (Popen object): agent subprocess
        msg (str): message

        """
        assert isinstance(msg, str)

        p = "".join([msg, '\n'])
        try:
            agent.stdin.write(p.encode())
        except Exception as e:
            print("Failed to send agent process message", msg, ".")
            raise
        
    def shutdown_agent(self, agent_num):
        """Issue shutdown command to agent.

        agent_num (int): index of agents[]

        """
        data = "-1" # -1 = shutdown
        self.send_message(agent_num, data)

        
#####testing  -- To facilitate testing, create new game with human client,
        # then run manager.py.
if __name__ == '__main__':
    
    import time
    #onload, create an AI in game 0.
    mgr = AIManager()
    
    #mgr.create_agent_for_new_game(0) # Uncomment this line to have AI-only game
    time.sleep(1)
    for i in [1,2,3]:
        mgr.create_agent_for_existing_game(0,0,i)
    #when mgr is destroyed, all agents shutdown(), so...
    #use below for long testing

    input("Press enter to kill manager....             ")
