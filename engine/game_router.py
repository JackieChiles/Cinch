#!/usr/bin/python3
"""Game router for Cinch.

TODO: add threading/async capes -- mostly handled already by CometServer?
        will want to Lock() games during pre-game events to avoid race problems

"""
# All import paths are relative to the root
from core.game import Game
from web.message import Message
from web.channel import CommChannel
from engine.client_manager import ClientManager


# Message signatures
SIGNATURE_NEW_GAME = ['game']
SIGNATURE_JOIN_GAME = ['join', 'pNum']
###SIGNATURE_GAME_ACTION = []

cm = ClientManager()


class GameRouter:
    """Manage handlers for traffic between games and clients."""
    def __init__(self):
        self.games = dict() #will be of format {gameid: game object}
        self.handlers = []

        # Create pre-game handlers
        self.handlers.append(NewGameHandler(self, SIGNATURE_NEW_GAME))
        self.handlers.append(JoinGameHandler(self, SIGNATURE_JOIN_GAME))
        
        #not ready to be implemented
        #self.handlers.append(GameEventHandler(self, SIGNATURE_GAME_ACTION))

        #used for getting data from Game and sending to server
        self.handlers.append(GameNotificationHandler(self))

    def register_handlers(self, server):
        """Register handlers with the web server.

        Call subclasses' register() for each subclass.

        server (CometServer): web server

        """
        for h in self.handlers:
            h.register(server)

    ##any other game management functions

#--------------------
# Base class for game router internal handlers
#--------------------
class GameRouterHandler(CommChannel):
    def __init__(self, router, signature=None):
        """
        router (GameRouter): reference to game router object
        signature (list): message signature to be handled
        """
        CommChannel.__init__(self)

        self.router = router
        self.signature = signature

 
#--------------------
# Handlers for specific message types / actions
#--------------------
class NewGameHandler(GameRouterHandler):    ####untested
    """React to new game messages from server."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)

    def respond(self, msg):
        """Handle new game request."""
        if msg.data['game'] != 0:   #just in case
            return
        
        #create new game object and add to router.games and client_mgr
        new_game = Game()
        game_id = cm.create_group()
        self.router.games[game_id] = new_game

        #generate GUID for requesting client, add to cm
        #add game to client in cm
        #set pNum for client in cm -- setting to 0 for now
        client_id = cm.create_client()
        cm.add_client_to_group(client_id, game_id)
        cm.set_client_player_num(client_id, 0)

        #return dict with client GUID and player number
        return {'uid': client_id, 'pNum': 0}


class JoinGameHandler(GameRouterHandler):  ###untested
    """React to client requests to join a game."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)

    def respond(self, msg):
        """Handle client request to join game."""
        #inspect target game to see if requested pNum is open
        #if not return error
        ## for current version, ignore requested pNum and manually assign one

        # Locate available seat in game and assign to pNum
        group_id = msg.data['join']
        cur_player_nums = set(cm.
                              get_player_nums_in_group(group_id))

        poss_nums = set([x for x in range(0,3)])  #avoid hardcoding
        avail_nums = poss_nums - cur_player_nums

        try:
            pNum = list(avail_nums)[0]
        except Exception:
            return {'err': "Game is full."}

        #generate GUID for requesting client, add to cm
        client_id = cm.create_client()

        #add client to game in cm
        cm.add_client_to_group(client_id, group_id)
        
        #set pNum for client in client manager
        cm.set_client_player_num(client_id, pNum)

        #check if game is full. if so, trigger game start (after short delay)
        if len(cm.groups[group_id]) == 4:   #don't hardcode this
            pass

        #return dict with client GUID and assigned player number
        return {'uid': client_id, 'pNum': pNum}

        
#not ready to implement this
class GameEventHandler(GameRouterHandler):
    """Handle in-game events. Break this out into smaller bits later."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)
        server.add_announcer(self)

    def respond(self, msg):
        """Handle in-game actions (bid/play)"""
        #match client GUID to game and player number

        #build message with that info

        #send message to Game (perhaps with Game having internal handler
        # a la Comet server?)

        #return
        return None


## need way for Game object to know to use this
class GameNotificationHandler(GameRouterHandler):
    """Receive data from Game and package in message for server."""
    # Overriden members
    def register(self, server):
        server.add_announcer(self)

    def respond(self, msg):
        """Package msg with appropriate destination info and send to server."""
        #expects msg with dest_list of pNums
        #source will be gameNum
        assert isinstance(msg, Message)
        assert isinstance(msg.dest_list, list)

        #get client GUIDs from cm based on gameNum, pNums        
        players_list = cm.groups[msg.source]
        dest_clients = []
        for p in players_list:
            if cm.get_player_num_by_client(cm[p]) in msg.dest_list:
                dest_clients.append(p)

        #build Message with dest_list = [client_guids] and data
        out = Message(msg.data, dest_list=dest_clients)

        #call self.announce with new message
        self.announce(out)
