#!/usr/bin/python2
"""Management system for Cinch AI agents.

-- needs to provide web client (via server) with list of available agents
-- needs to instantiate agents on request from server
---- agent must be instructed to join certain room & seat

Method reference:

import_module
get_ai_models
set_ai_ident

AIManager:
setupSocket
on_getAIList
on_summonAI
get_ai_summary

"""
from socketIO_client import SocketIO, BaseNamespace

import os
import imp # Import module functionality
import sys
import threading
import string

from time import sleep

import logging
log = logging.getLogger(__name__)

from common import SOCKETIO_PORT, SOCKETIO_NS

MY_PATH = os.path.abspath(os.path.dirname(__file__))
MODELS_FILE = "available_models.txt"


def import_module(module_name):
    """Import module from file and return module object.
    Copied (mostly) from docs.python.org.

    module_name (string) -- the name of the module (filename minus extention)

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
    """Load AI classes into namespace using contents of available AI file."""
    # Open and parse models file
    log.info("Reading {0} for AI models...".format(MODELS_FILE))
    with open(os.path.join(MY_PATH, MODELS_FILE)) as fin:
        lines = fin.readlines()

    lines = map(string.strip, lines)  # Remove newline characters
    aiFiles = filter(lambda x: len(x) > 0, lines) # Remove blank lines

    # Import each file into a module
    filenameToModuleName = lambda f: os.path.splitext(f)[0]
    moduleNames = map(filenameToModuleName, aiFiles) # Prepare module names
    aiModules = map(import_module, moduleNames) # Load modules

    map(set_ai_ident, aiModules) # Set identity of each AI class

    # Produce log messages
    map(log.info, map(
        lambda x: "AI Agent {0} imported.".format(x), moduleNames))

    return list(map(lambda m: getattr(m, m.AI_CLASS), aiModules))

def set_ai_ident(mod):
    """Set a self.identity for the AI class within the specified module.

    mod -- module for an AI agent

    """
    cls = getattr(mod, mod.AI_CLASS)
    cls.identity = {  'author':   mod.__author__,
                      'version':  mod.__version__,
                      'date':     mod.__date__,
                      'skill':    mod.__skill__,
                      'name':     mod.__agent_name__,
                      'description':  mod.__description__
    }


class AIManager:

    """Management entity for AI agents."""

    def __init__(self):
        self.aiClasses = get_ai_models()
        self.aiSummary = self.get_ai_summary()

        self.setupSocket()

        log.info("AI Management Agency open, hosting {0} agents".format(
            len(self.aiClasses)))

        self.socket.wait() # Blocks

    def setupSocket(self):
        # The AIMgr thread is started before the main server due to reasons.
        # Pause a moment to let the main server come up before the Manager
        # connects.
        sleep(1)

        self.socket = SocketIO('127.0.0.1', SOCKETIO_PORT)
        self.ns = self.socket.define(BaseNamespace, SOCKETIO_NS)

        # Attach socketIO event handlers
        self.ns.on('getAIList', self.on_getAIList)
        self.ns.on('summonAI', self.on_summonAI)

        self.ns.emit('nickname', 'AIManager')
        self.ns.emit('join', 0, 0) # Join lobby

    def on_getAIList(self, *args):
        """Provide AI identity information to game server."""
        self.ns.emit('aiListData', self.aiSummary)

    def on_summonAI(self, *args):
        """Spawn AI agent for a game using threading.

        args -- {room number: (seat, AI model ID)}

        """
        val = args[0]
        roomNum = int(val.keys()[0])
        seat = val.values()[0][0]
        modelID = val.values()[0][1]

        # FUTURE: If performance is poor, rework to use sub/multiprocessing
        # instead of threading for AI agents.
        agent = threading.Thread(target=self.aiClasses[modelID-1],
                                 args=(roomNum, seat))
        agent.daemon = True
        agent.start()

    def get_ai_summary(self):
        """Assemble data for choosing/viewing available AI Agents.

        Uses data contained in self.ai_packages to send to client. Client will
        use data to build AI Agent selection elements to be used when making
        new games. All data should be triple-underscored.

        Information will be requested by client using the 'aiList' event.

        """
        aList = []
        temp = {}
        i = 1 # Used for AI ID #

        for ai_class in self.aiClasses:
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
