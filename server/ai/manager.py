#!/usr/bin/python2

"""Management system for Cinch AI agents.

The AI Manager itself blocks its thread after it is initialized. This is needed
to maintain connection to a socket server, so AIManager should be started in a
separate thread.

The AI Manager provides two main functions:
- It provides a list of available AI models to the server
- It creates AI agents at the request of a client (via the server)
    - Agents are told what room to join and seat to take

AI information is assembled by the Manager by inspecting the Python source
files for all available agents. Available agents are specified in
MODELS_FILE. This allows agents to be (de-)activated in a plain text file
without changing source code. However, the MODELS_FILE is only read when the
server (and hence the Manager) is first started, so the available AI models
cannot be changed without a server restart.

Agents are instantiated on a separate thread and given instructions on what
room to join. After initializing an AI agent, agents can only communicate via
the common socketio interface; the Manager does not keep a reference to the
agent's thread.

FUTURE: If performance is poor, it may be possible to rework to use
multiprocessing instead of threading. This would circumvent Python's
interpreter lock and let more CPU cores be used.

Attributes:
  log (Logger): Log interface common to all Cinch modules.
  MY_PATH (str): The absolute path of this code file.
  MODELS_FILE (str): The file path of the available AI models text file.

Public classes:
  AIManager: Entity for managing AI models.

Public methods:
  import_module: Given a module name, import and return the module.
  get_ai_models: Use MODELS_FILE to import AI modules.
  set_ai_ident: Set AI.ident for a given module.

"""


import logging
log = logging.getLogger(__name__)

import os
import imp  # Import module functionality
import sys
import threading
import string

from time import sleep
from socketIO_client import SocketIO, BaseNamespace

from common import SOCKETIO_PORT, SOCKETIO_NS

MY_PATH = os.path.abspath(os.path.dirname(__file__))
MODELS_FILE = "available_models.txt"


def import_module(module_name):
    """Import module from file and return module object.

    Copied (mostly) from docs.python.org. This allows the dynamic import of
    modules using a name variable.

    Args:
      module_name (string): The name of the module (filename minus extention).

    Returns:
      module: The imported module.

    """
    # In case something with module name is in global NS, remove it
    if module_name in sys.modules:
        del sys.modules[module_name]

    fp, pathname, desc = imp.find_module(module_name, [MY_PATH, ])

    try:
        # This has the same result as calling 'import foo'
        return imp.load_module(module_name, fp, pathname, desc)
    finally:
        if fp:
            fp.close()


def get_ai_models():
    """Load AI classes into namespace. Return list of modules.

    The MODELS_FILE is read for available AI agent module names. Each module
    is imported dynamically and that module's AI identity is set.

    Returns:
      list: References to each AI class contained within the imported modules.

    """
    log.info("Reading {0} for AI models...".format(MODELS_FILE))
    with open(os.path.join(MY_PATH, MODELS_FILE)) as fin:
        lines = fin.readlines()

    # Sanitize file data; models can be commented out with '#'
    lines = map(string.strip, lines)
    aiFiles = filter(lambda x: len(x) > 0 and x[0] != "#", lines)

    # Import each file into a module and set identity data
    filenameToModuleName = lambda f: os.path.splitext(f)[0]
    moduleNames = map(filenameToModuleName, aiFiles)
    aiModules = map(import_module, moduleNames)
    map(set_ai_ident, aiModules)

    map(log.info,
        map(lambda x: "AI Agent {0} imported.".format(x), moduleNames))

    return list(map(lambda m: getattr(m, m.AI_CLASS), aiModules))


def set_ai_ident(mod):
    """Set self.identity for the AI class within the specified module.

    Args:
      mod (module): The module for the target AI agent.

    """
    cls = getattr(mod, mod.AI_CLASS)
    cls.identity = dict(author=mod.__author__,
                        version=mod.__version__,
                        date=mod.__date__,
                        skill=mod.__skill__,
                        name=mod.__name__,
                        description=mod.__description__)
    return


class AIManager(object):
    """Management entity for AI agents.

    The Manager stays alive as long as the server is running. After providing
    the server with the available AI info at startup, it creates new AI
    instances on-demand.

    Attributes:
      aiClasses (list): List of pointers to available AI classes (not modules).
      aiSummary (list): AI identity data, prepared for the server.
      socket (SocketIO): Socket connection for communicating with server.
      ns (BaseNamespace): Socket namespace used by socket.

    """
    def __init__(self):
        """Initialize AIManager.

        The Manager imports and summarizes all available AI agents, then sets
        up its socket and namespace. Finally, socket.wait() is called, which
        blocks the current thread.

        """
        self.aiClasses = get_ai_models()
        self.aiSummary = self.get_ai_summary()
        self.setupSocket()

        log.info("AI Management Agency open, hosting {0} agents".format(
            len(self.aiClasses)))

        self.socket.wait()  # Blocks

    def setupSocket(self):
        """Create socket connection and send configuration data to server.

        After connecting to the server, the Manager transmits AI summary data,
        requests a nickname, and joins the Lobby.

        """
        # In the current configuration, the AI Manager thread is started before
        # the main socket server, since starting the main server is the final
        # blocking action performed in cinch.py. A sleep is used to give the
        # main server time to come online before the Manager tries to connect.
        sleep(1)

        self.socket = SocketIO('127.0.0.1', SOCKETIO_PORT)
        self.ns = self.socket.define(BaseNamespace, SOCKETIO_NS)

        # Attach socketIO event handlers
        self.ns.on('summonAI', self.on_summonAI)

        self.ns.emit('aiListData', self.aiSummary)
        self.ns.emit('nickname', 'AIManager')
        self.ns.emit('join', 0, 0)  # Room 0 is the Lobby

    def on_summonAI(self, data):
        """Handle request from server for an AI agent.

        Threading is used to spawn a new AI agent for a game.

        Args:
          data (dict): Data of the format `{room number: (seat, AI model ID)}`,
            where all values are integers.

        """
        roomNum = data.keys()[0]
        seat = data[roomNum][0]
        modelID = data[roomNum][1]

        # Model IDs are base 1, while aiClasses is base 0
        agent = threading.Thread(target=self.aiClasses[modelID-1],
                                 args=(int(roomNum), seat))
        agent.daemon = True
        agent.start()

    def get_ai_summary(self):
        """Return data detailing available AI agents.

        Returns:
          list: Each element is a dict of AI identifying information, found in
            the identity attribute of the AI class.

        """
        aList = []
        temp = {}

        for i, ai_class in enumerate(self.aiClasses):
            ident = ai_class.identity
            temp = {'id': i+1,
                    'auth': ident['author'],
                    'ver':  ident['version'],
                    'date': ident['date'],
                    'skl':  ident['skill'],
                    'name': ident['name'],
                    'desc': ident['description']}
            aList.append(temp)

        return aList
