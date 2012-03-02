#!/usr/bin/python3
"""Game router for Cinch.

TODO: add threading/async capes -- mostly handled already by CometServer?
        will want to Lock() games during pre-game events to avoid race problems
        (might not be an issue one game lobby implemented)

TODO: implement way to connect AIs into game_router; seems like the best access
        point.

"""
from threading import Timer #for delayed start

# All import paths are relative to the root
import core.common as common
from core.game import Game, NUM_PLAYERS
from web.message import Message
from web.channel import CommChannel

MAX_GAME_SIZE = NUM_PLAYERS # Max number of players in a game
START_GAME_DELAY = 5.0 # Time to wait between last player joining and starting

# Message signatures
SIGNATURE = common.enum(
                NEW_GAME=['game'],
                JOIN_GAME=['join', 'pNum'],
                GAME_PLAY=['card'],
                BID=['bid']
                )


class GameRouter:
    """Manage handlers for traffic between games and clients."""
    def __init__(self):
        self.games = dict() #will be of format {gameid: game object}
        self.handlers = []

    def attach_client_manager(self, cm):
        """Attach client manager from the engine to Game Router.

        cm (ClientManager): Client Manager created at the root level

        """
        self.client_mgr = cm

    def register_handlers(self, server):
        """Create and register handlers with the web server.

        Call subclasses' register() for each subclass.

        server (CometServer): web server

        """
        if self.client_mgr is None:
            raise RuntimeError("Client Manager not attached to Game Router.")
        
        # Create action handlers
        self.handlers.append(NewGameHandler(self, SIGNATURE.NEW_GAME))
        self.handlers.append(JoinGameHandler(self, SIGNATURE.JOIN_GAME))        
        self.handlers.append(GamePlayHandler(self, SIGNATURE.GAME_PLAY))
        self.handlers.append(BidHandler(self, SIGNATURE.BID))
        #used for getting data from Game and sending to server
        ##self.handlers.append(GameNotificationHandler(self))

        # Register each handler with the Comet server
        for h in self.handlers:
            h.register(server)


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
        self.client_mgr = router.client_mgr

 
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
        if msg.data['game'] != '0':
            # May support other types of game requests in the future
            return

        cm = self.client_mgr
        
        # Create new game object and add to router.games and client_mgr
        new_game = Game()
        game_id = cm.create_group()
        self.router.games[game_id] = new_game
        
        # Create GUID for requesting client and add entry to client_mgr
        client_id = cm.create_client()
        cm.add_client_to_group(client_id, game_id)
        cm.set_client_player_num(client_id, 0)

        # Return client GUID and player number via POST
        return {'uid': client_id, 'pNum': 0}


class JoinGameHandler(GameRouterHandler):  ###untested
    """React to client requests to join a game."""
    # Overriden members
    def register(self, server):
        server.add_responder(self, self.signature)

    def respond(self, msg):
        """Handle client request to join game."""
        cm = self.client_mgr

        ##########
        ## for current version, ignore requested pNum and manually assign one
        ##########
        
        # Locate available seat in game and manually assign to pNum
        game_id = int(msg.data['join'])
        cur_player_nums = set(cm.get_player_nums_in_group(game_id))

        poss_nums = set([x for x in range(0,MAX_GAME_SIZE)])
        avail_nums = poss_nums - cur_player_nums

        try:
            pNum = list(avail_nums)[0]
        except Exception:
            return {'err': "Game is full."}

        ############## delete preceeding block when following block becomes enabled

##        ############## untested
##        # TODO: uncomment this block once client allows players to select seat
##        #############
##        
##        # Check if requested seat is a valid seat
##        requested_pNum = int(msg.data['pNum'])
##        poss_nums = [x for x in range(0, MAX_GAME_SIZE)]
##        if requested_pNum not in poss_nums:
##            return {'err': "Selected seat not valid."}
##
##        # Get list of currently occupied seats in target game
##        game_id = int(msg.data['join'])
##        cur_player_nums = cm.get_player_nums_in_group(game_id)
##
##        # Check if game is full
##        if len(poss_nums) == len(cur_player_nums):
##            return {'err': "Game is full."}
##        # Check if requested seat is occupied
##        if requested_pNum in cur_player_nums:
##            return {'err': "Seat {0} is already occupied.".format(
##                                                            requested_pNum)}
##
##        # pNum is valid selection
##        pNum = requested_pNum
##        


        # Create GUID for requesting client and add entry to client_mgr
        client_id = cm.create_client()
        cm.add_client_to_group(client_id, game_id)
        cm.set_client_player_num(client_id, pNum)

        # Check if game is now full. If so, trigger and announce game start
        if len(cm.groups[game_id]) == MAX_GAME_SIZE:
            # After short delay (so last client to join can receive uid/pNum
            # response from return statement) start game and send clients
            # game-start info (hands, active player, etc.)
            def launch_game(self, game_id):
                init_data = self.router.games[game_id].start_game()
                #for item in init_data: #uncomment once start_game() is done
                #    m = Message(relevant stuff from init_data)
                #need to register announcer if this is how we want to do this
                #    self.announce(m) 

            t = Timer(START_GAME_DELAY, launch_game, args=[self, game_id])
            t.start()

        # Return client GUID and assigned player number
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
        cm = self.client_mgr
        
        # Match client GUID to game id and player number
        game_id = cm.get_group_by_client(msg.source)
        target_game = self.router.games[game_id]
        pNum = cm.get_player_num_by_client(msg.source)

        # Pass info to Game to call play processing logic
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
        cm = self.client_mgr
        
        #match client GUID to game and player number -- inspect GamePlayHandler
        # when done for encapsulation options
        game_id = cm.get_group_by_client(msg.source)
        target_game = self.router.games[game_id]
        pNum = cm.get_player_num_by_client(msg.source)

        #send message to Game
        
        #response = target_game.handle_bid(pNum, msg.data)

        #interpret response from Game

        #return
        return None
    

## TODO: need way for Game object to know to use this -- if needed!
    # will there be any cases where Game creates data NOT in response to player
    # action? player action includes AI action (hopefully)
class GameNotificationHandler(GameRouterHandler):
    """Receive data from Game and package in message for server."""
    # Overriden members
    def register(self, server):
        server.add_announcer(self)

    def respond(self, msg):
        """Package msg with appropriate destination info and send to server."""
        cm = self.client_mgr
        
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
