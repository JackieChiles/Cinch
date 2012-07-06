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

        ai_path = os.path.join(os.getcwd(), "ai") #currently in root

        self.ai_path = ai_path #store value for later use
        
        dirlist = os.listdir(ai_path)

        # Remove __pycache__ and _demo from candidate packages, if present
        try:    dirlist.remove('__pycache__')
        except: pass
        try:    dirlist.remove('_demo')
        except: pass

        curDir = os.getcwd()
        os.chdir(ai_path) # Filtering needs to be performed from AI directory
        
        # Filter non-directories from dirlist
        packages = filter(os.path.isdir, dirlist)

        # Gather ID info from each package (___things from __init__.py)
        for pkg in packages:
            d = {'pkg': pkg}
            # Read pgk/__init__.py for triple-underscored values;
            # these are descriptor values
            p = os.path.join(ai_path, pkg, "__init__.py")
            with open(p, mode='r') as fp:
                for line in iter(fp.readline, ''):
                    if line[:3] == "___":
                        exec(line, globals(), d) # add line to d
            self.ai_packages.append(d)

        os.chdir(curDir) # Change to old working directory (may be unneeded)

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

        #TODO: may want to sort ai_packages first
        for pkg in self.ai_packages:  
            temp = {'id': i,
                    'auth': pkg['___author'],
                    'ver': pkg['___version'],
                    'date': pkg['___date'],
                    'skl': pkg['___skill'],
                    'name': pkg['___agent_name'],
                    'desc': pkg['___description']
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
            return None #TODO will need to handle this in a useful way

        model_num = model_num - 1 # IDs sent to client start at 1, not 0

        # Change to AI directory
        curDir = os.getcwd()
        os.chdir(self.ai_path)
        
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
            os.chdir(curDir) # return to previous directory (may be unneeded)
            
            return agent

    def create_agent_for_existing_game(self, model_num, game_id, pNum):
        """Create new agent and issue 'join game' command to it.

        model_num (int): index of desired agent in available agent models
        game_id (int): id of target game for new agent
        
        """
        agent = self.create_agent(model_num)

        data = "2|{0}|{1}".format(game_id, pNum) # 2 = join game

        # Issue 'join game' command -- arguments are pipe delimited
        self.send_message(agent, data)    

    #This option is currently inactive, as new game requests require a 'plrs' parameter
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

#Manager no longer functions in stand-alone mode
