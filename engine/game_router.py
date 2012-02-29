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

MAX_GAME_SIZE = 4 # Max number of players in a game
# Message signatures
SIGNATURE_NEW_GAME = ['game']
SIGNATURE_JOIN_GAME = ['join', 'pNum']
SIGNATURE_GAME_PLAY = ['card']
#SIGNATURE_BID = []
#SIGNATURE_GAME_ACTION = []

cm = ClientManager()


class GameRouter:
    """Manage handlers for traffic between games and clients."""
    def __init__(self):
        self.games = dict() #will be of format {gameid: game object}
        self.handlers = []

        self.games = [] #list of (game_id, game_object) tuples

        # Create pre-game handlers
        self.handlers.append(NewGameHandler(self, SIGNATURE_NEW_GAME))
        self.handlers.append(JoinGameHandler(self, SIGNATURE_JOIN_GAME))
        
        self.handlers.append(GamePlayHandler(self, SIGNATURE_GAME_PLAY))

        #used for getting data from Game and sending to server
        ##self.handlers.append(GameNotificationHandler(self))

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
class NewGameHandler(GameRouterHandler):
    """React to new game messages from server."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)

    def respond(self, msg):
        """Handle new game request."""
        if msg.data['game'] != '0':   #just in case
            return
        
        #create new game object and add to router.games and client_mgr
        ##new_game = Game()
        new_game = None #TODO: change once Game works
        game_id = cm.create_group()
        self.router.games[game_id] = new_game
        
        #generate GUID for requesting client, add to cm
        #add game to client in cm
        #set pNum for client in cm -- setting to 0 for now
        client_id = cm.create_client()
        cm.add_client_to_group(client_id, game_id)
        cm.set_client_player_num(client_id, 0)

        #add reference to Game object to game_router (for later Msg routing)
        self.router.games.append((game_id, new_game))

        #return dict with client GUID and player number
        return {'uid': client_id, 'pNum': 0}


class JoinGameHandler(GameRouterHandler):  ###untested
    """React to client requests to join a game."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)

    def respond(self, msg):
        """Handle client request to join game."""
        #TODO: inspect target game to see if requested pNum is open
        #if not return error
        ## for current version, ignore requested pNum and manually assign one

        # Locate available seat in game and assign to pNum
        group_id = int(msg.data['join'])
        cur_player_nums = set(cm.
                              get_player_nums_in_group(group_id))

        poss_nums = set([x for x in range(0,MAX_GAME_SIZE)])
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
        if len(cm.groups[group_id]) == MAX_GAME_SIZE:
            #start game
            pass

        #return dict with client GUID and assigned player number
        return {'uid': client_id, 'pNum': pNum}


#this logic needs to be handled w/in the Game object; re-encapsulate data here,
# then call handler w/in Game; a response must be returned to here
class GamePlayHandler(GameRouterHandler):
    """Handle plays made (cards) during game."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)
        server.add_announcer(self)

    def respond(self, msg):
        """Handle plays."""
        #match client GUID to game and player number
        game_id = cm.get_group_by_client(msg.source)
        target_game = self.router.games[game_id]
        pNum = cm.get_player_num_by_client(msg.source)

        #build message with that info to send to appropos Game
        #for each x in SIGNATURE_game_play, add {x:val} to data
        data = dict()
        for x in SIGNATURE_GAME_PLAY:
            data[x] = msg.data[x]

        new_msg = Message(data, source=pNum, dest=game_id)

        #send message to Game / call play processing logic
        response = target_game.handle_card_played(new_msg)
        #response could be a dict, list of tuples, or whatnot. will use to
        #build message(s) to be announced to server

        #for each response element, get target client guid

        #announce each message not specifically addressed to client

        #will return error
        ## Drew: i know we want to use return for errors, but what about PMs
        ## to calling client; should we reuse the connection, or do the chat
        ## approach and announce all?
        return None


#not ready to implement this
class BidHandler(GameRouterHandler):
    """Handle plays made during game."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)
        server.add_announcer(self)

    def respond(self, msg):
        """Handle bids."""
        #match client GUID to game and player number

        #build message with that info

        #send message to Game (perhaps with Game having internal handler
        # a la Comet server?)

        #return
        return None


##will need handler for other game actions: setting trump, ....?
    

## TODO: need way for Game object to know to use this
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
