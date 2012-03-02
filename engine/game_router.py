#!/usr/bin/python3
"""Game router for Cinch.

TODO: add threading/async capes -- mostly handled already by CometServer?
        will want to Lock() games during pre-game events to avoid race problems
        (might not be an issue one game lobby implemented)

TODO: implement way to connect AIs into game_router; seems like the best access
        point.

"""
# All import paths are relative to the root
import core.common as common
from core.game import Game, NUM_PLAYERS
from web.message import Message
from web.channel import CommChannel
from engine.client_manager import ClientManager

MAX_GAME_SIZE = NUM_PLAYERS # Max number of players in a game

# Message signatures
SIGNATURE = common.enum(
                NEW_GAME=['game'],
                JOIN_GAME=['join', 'pNum'],
                GAME_PLAY=['card'],
                BID=['bid']
                )

cm = ClientManager()


class GameRouter:
    """Manage handlers for traffic between games and clients."""
    def __init__(self):
        self.games = dict() #will be of format {gameid: game object}
        self.handlers = []

        # Create pre-game handlers -- these get connected to Comet Server
        self.handlers.append(NewGameHandler(self, SIGNATURE.NEW_GAME))
        self.handlers.append(JoinGameHandler(self, SIGNATURE.JOIN_GAME))        
        self.handlers.append(GamePlayHandler(self, SIGNATURE.GAME_PLAY))
        self.handlers.append(BidHandler(self, SIGNATURE.BID))
        #used for getting data from Game and sending to server
        ##self.handlers.append(GameNotificationHandler(self))

    def register_handlers(self, server):
        """Register handlers with the web server.

        Call subclasses' register() for each subclass.

        server (CometServer): web server

        """
        for h in self.handlers:
            h.register(server)
            
    def get_client_guids(self, guid):
        return cm.get_clients_in_group(cm.get_group_by_client(guid))

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
        game_id = int(msg.data['join'])
        cur_player_nums = set(cm.
                              get_player_nums_in_group(game_id))

        poss_nums = set([x for x in range(0,MAX_GAME_SIZE)])
        avail_nums = poss_nums - cur_player_nums

        try:
            pNum = list(avail_nums)[0]
        except Exception:
            return {'err': "Game is full."}

        #generate GUID for requesting client, add to cm
        client_id = cm.create_client()

        #add client to game in cm
        cm.add_client_to_group(client_id, game_id)
        
        #set pNum for client in client manager
        cm.set_client_player_num(client_id, pNum)

        #check if game is full. if so, trigger game start (after short delay)
        if len(cm.groups[game_id]) == MAX_GAME_SIZE:
            #start game
            pass

        #
        #TODO: actually need to join player to Game object (create Player)
        # -- maybe create all players at once when game is started, to avoid
        #       having to remove players from Game if they drop
        
        #return dict with client GUID and assigned player number
        return {'uid': client_id, 'pNum': pNum}

#####
#TODO: Implement way to drop from game before/after game start
#####
    
    
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

        #send info to Game / call play processing logic
        card_num = msg.data['card']
        response = target_game.handle_card_played(pNum, card_num)
        
        #response will be list of dicts of game state data; will use to
        #build message(s) to send out.
        outgoing_msgs = []

        #TODO: once the format Game makes messages is standardized,
        #encapsulate the following message building code; will be reused
        #FGJ in bid handler.
        
        #broadcast message to all players in game OR error message to caller
        if len(response) == 1: #or response is not a list, just a single dict?
                                #or response == False??
            #if response is error message
            #    return error message to msg.source

            # Broadcast message to all players in game
            dest = cm.get_clients_in_group(game_id)
            data = None ##***
            outgoing_msgs.append(Message(data, source=game_id, dest_list=dest))

        else:   # Private message for each client / Multi-cast
                #TODO: if the message for multiple clients is the same,
                #       combine the destinations into one message
            for element in response:
                dest_pNum = element['target'] #for example
                dest = cm.get_client_by_player_num(game_id, dest_pNum)
                data = None ##***
                outgoing_msgs.append(
                    Message(data, source=game_id, dest_list=[dest]))
        
        #announce each non-error message
        for x in outgoing_msgs:
            self.announce(x)
        
        return None


#not ready to implement this, will follow same scheme as gameplay handler
class BidHandler(GameRouterHandler):
    """Handle plays made during game."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)
        server.add_announcer(self)

    def respond(self, msg):
        """Handle bids."""
        #match client GUID to game and player number
        game_id = cm.get_group_by_client(msg.source)
        target_game = self.router.games[game_id]
        pNum = cm.get_player_num_by_client(msg.source)

        #send message to Game
        
        #response = target_game.handle_bid(pNum, msg.data)

        #interpret response from Game

        #return
        return None
    

## TODO: need way for Game object to know to use this
    # will there be any cases where Game creates data NOT in response to player
    # action? player action includes AI action (hopefully)
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
