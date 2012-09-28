#!/usr/bin/python3
"""Game router for Cinch.

File contents:

-class GameRouter
--attach_ai_manager()
--attach_client_manager()
--register_handlers()
--get_client_guids()

-class GameRouterHandler(CommChannel)
--register()
--announce_msgs_from_game()

-class ServerMonitor(CommChannel)
-class NewGameHandler(GameRouterHandler)
-class JoinGameHandler(GameRouterHandler)
-class LobbyHandler(GameRouterHandler)
-class AIListRequestHandler(GameRouterHandler)
-class GamePlayHandler(GameRouterHandler)
-class AIListRequestHandler(GameRouterHandler)

-get_error()


TODO: add threading/async capes -- mostly handled already by CometServer?


"""
from threading import Timer # For delayed start
from time import sleep, time
from _thread import start_new_thread # For timeout handler

import logging
log = logging.getLogger(__name__)

import core.common as common
import core.cards as cards
from core.game import Game, NUM_PLAYERS
from web.message import Message
from web.channel import CommChannel

MAX_GAME_SIZE = NUM_PLAYERS # Max number of players in a game
START_GAME_DELAY = 3.0 # Time to wait between last player joining and starting
DEFAULT_PNUM = 0 # pNum assigned to player who creates new game

GAME_TIMEOUT_INTERVAL = 60 # Secs to allow game to get no traffic before ending
                           # Ensure this exceeds COMET_TIMEOUT on server!

# Message signatures
SIGNATURE = common.enum(
    NEW_GAME = ['game', 'plrs', 'name'],
    JOIN_GAME = ['join', 'pNum', 'name'],
    LOBBY = ['lob'],
    GAME_PLAY = ['card'],
    BID = ['bid'],
    AI_LIST_REQUEST = ['ai']
    )

# Enum constants for building POST-response error messages
ERROR_TYPE = common.enum(
    FULL_GAME=1,
    INVALID_SEAT=2,
    OCCUPIED_SEAT=3,
    ILLEGAL_BID=4,
    ILLEGAL_PLAY=5
    )

# Global variables
ai_mgr = None   # Used for AI manager, assigned later
cm = None   # Used for client manager, assigned later


class GameRouter:
    """Manage handlers for traffic between games and clients."""
    def __init__(self):
        self.games = dict() # key=game_id, value=game object
        self.gametimes = dict() #key=game_id, value=last_time of client contact
        self.handlers = []
        
        # Start game timeout thread
        self.running = True
        start_new_thread(self.handle_timeout, ())
        
    def __del__(self):
        self.running = False

    def attach_ai_manager(self, ai):
        """Attach AI Manager from the engine to the Game Router module.

        ai (AIManager): AI manager created at the root level.

        """
        global ai_mgr
        ai_mgr = ai

    def attach_client_manager(self, client_mgr):
        """Attach client manager from the engine to Game Router.

        client_mgr (ClientManager): Client Manager created at the root level

        """
        global cm
        cm = client_mgr

    def register_handlers(self, server):
        """Create and register handlers with the web server.

        Call subclasses' register() for each subclass.

        server (CometServer): web server

        """
        if cm is None:
            raise RuntimeError("Client Manager not attached to Game Router.")

        # Create monitor for GET requests on server (used for game timeouts)
        server.monitor = ServerMonitor(self)
        
        # Create action handlers
        addHandler = self.handlers.append
        
        addHandler(NewGameHandler(self, SIGNATURE.NEW_GAME))
        addHandler(JoinGameHandler(self, SIGNATURE.JOIN_GAME))        
        addHandler(GamePlayHandler(self, SIGNATURE.GAME_PLAY))
        addHandler(BidHandler(self, SIGNATURE.BID))
        addHandler(LobbyHandler(self, SIGNATURE.LOBBY))
        addHandler(AIListRequestHandler(self, SIGNATURE.AI_LIST_REQUEST))

        # Register each handler with the Comet server
        for h in self.handlers:
            h.register(server)
            
    def get_client_guids(self, guid):
        return cm.get_clients_in_group(cm.get_group_by_client(guid))
        
    def handle_timeout(self):
        """Periodically check for "stale" games. Terminate any that have not
        received a GET request in the last GAME_TIMEOUT_INTERVAL. Games with
        AI players will (should) never go stale.
        
        """
        while self.running:
            now = time() // 1

            for game_id in list(self.gametimes):
                if (now - self.gametimes[game_id]) > GAME_TIMEOUT_INTERVAL:
                    # Cleanup self.games
                    del self.games[game_id]
                    # Cleanup self.gametimes
                    del self.gametimes[game_id]
                    # Cleanup client manager
                    cm.del_group(game_id)
                    
                    log.info("Game {0} timed out.".format(game_id))
            
            sleep(GAME_TIMEOUT_INTERVAL)
        

#--------------------
# Base class for game router internal handlers
#--------------------

class GameRouterHandler(CommChannel):
    def __init__(self, router, signature=None):
        """
        router (GameRouter): reference to game router object
        signature (list): message signature to be handled
        """
        super().__init__()

        self.router = router
        self.signature = signature

    def register(self, server):
        """
        server (CometServer): reference to web server

        """
        server.add_responder(self, self.signature)
        server.add_announcer(self)

    def announce_msgs_from_game(self, msg_list, game_id):
        """Build Messages from Game and announce to web server.

        msg_list (list of dicts): outgoing data; one element per destination
        game_id (int): id num of related Game

        """
        outgoing_msgs = []
        for element in msg_list:
            dest_pNum = element.pop('tgt')
            for target in dest_pNum:
                # Convert pNum to uid
                dest = cm.get_client_by_player_num(game_id, target)
                outgoing_msgs.append(
                    Message(element, target=dest, source=game_id))
    
        # Announce each message
        for m in outgoing_msgs:
            self.announce(m)


#--------------------
# Handlers for specific message types / actions
#--------------------
class ServerMonitor(CommChannel):
    """Listens to all GET requests made on the server for guids & updates
    timeout information for active games."""
    def __init__(self, router):
        super().__init__()
        self.router = router # router = GameRouter
        
    # Overriden member
    def respond(self, guid):
        # Get game id of client
        game_id, _ = cm.get_client_info(guid)
        if game_id is not None:
            # Update last timestamp of game
            self.router.gametimes[game_id] = time() // 1
        
        
class NewGameHandler(GameRouterHandler):
    """React to New Game requests from server."""
    # Overridden member
    def respond(self, msg):
        
        if msg.data['game'] != '0':
            # May support other types of game requests in the future
            return None

        ######
        # TODO-FUTURE: Set limit on # concurrent games and enforce limit here.
        ######

        # Create new game object and add to router.games and client_mgr
        new_game = Game()
        game_id = cm.create_group()
        self.router.games[game_id] = new_game
        
        # Create GUID for requesting client and add entry to client_mgr
        #TODO-FUTURE: don't use default pnum, let game creator decide?
        client_id = cm.create_client(name=msg.data['name'])
        cm.add_client_to_group(client_id, game_id, DEFAULT_PNUM)

        # Handle 'plrs' list, creating AI agents as needed
        player_options = list(map(int, msg.data['plrs'].split(',')))
        for index, val in enumerate(player_options):
            if val > 0: # humans < 0, AIs > 0, 0 unused
                # Create AI in pNum index with agent val
                ai_mgr.create_agent_for_existing_game(val, game_id, index)

        # Return client GUID and player number via POST
        return {'uid': client_id, 'pNum': DEFAULT_PNUM} 


class JoinGameHandler(GameRouterHandler):
    """React to client requests to join a game."""
    # Overriden member
    def respond(self, msg):
        # Check if game is full
        game_id = int(msg.data['join'])
        if game_id == -1: # -1 = join newest game
            game_id = len(self.router.games) - 1

        cur_player_nums = cm.get_player_nums_in_group(game_id)       
        
        if len(cur_player_nums) == MAX_GAME_SIZE:
          return get_error(ERROR_TYPE.FULL_GAME)

        # Check if requested seat is a valid seat
        requested_pNum = int(msg.data['pNum'])
        if requested_pNum not in range(MAX_GAME_SIZE):
          return get_error(ERROR_TYPE.INVALID_SEAT, requested_pNum)

        # Check if requested seat is occupied
        if requested_pNum in cur_player_nums:
          return get_error(ERROR_TYPE.OCCUPIED_SEAT, pNum)

        # pNum is valid selection
        pNum = requested_pNum

        # Create GUID for requesting client and add entry to client_mgr
        client_id = cm.create_client(name=msg.data['name'])
        if client_id is None:
            return {'err':
                    'Server unable to handler more players. Try again later.'}
      
        # Prepare list of folks already in game for new client
        names = []
        players = cm.get_player_names_in_group(game_id)
        for key in players:
            names.append({'pNum': key, 'name': players[key]})
        name_msg = Message({'names':names}, target=client_id, source=game_id)
        self.announce(name_msg)
      
        # Announce new player entering game
        tgts = cm.get_clients_in_group(game_id)
        for tgt in tgts:
            out_data = {'names': [ {'name': msg.data['name'], 'pNum': pNum} ]}
            self.announce(Message(out_data, target=tgt, source=game_id))

        # Notify client manager
        cm.add_client_to_group(client_id, game_id, pNum)
        
        # Check if game is now full. If so, trigger and announce game start
        if len(cm.groups[game_id]) == MAX_GAME_SIZE:
            players = cm.get_player_names_in_group(game_id)
            
            init_data = self.router.games[game_id].start_game(players)
            self.announce_msgs_from_game(init_data, game_id)
            log.info("Game Router: game started")           

        # Return client GUID and assigned player number
        return {'uid': client_id, 'pNum': pNum}


#####
#TODO: Implement way to drop from game before/after game start
#TODO: These handlers need to make better use of constants for strings.
#####

class LobbyHandler(GameRouterHandler):
    """React to game lobby requests from client."""
    # Overridden member
    def respond(self, msg):
        
        if msg.data['lob'] != '0':
            # May support other types of game lobby requests in the future.
            # For now, '0' is just a request for all current games
            return None
            
        games = []
        
        for group_id in cm.groups.keys():
            client_group = cm.groups[group_id]
            players = []
            for pNum in client_group:
                # Prepare client_group info for Cinch client
                guid = client_group[pNum]
                players.append({'name': cm.clients[guid].name,
                                'num': cm.clients[guid].pNum})
            games.append({'num': group_id, 'plrs': players})
        
        # Return game list via POST (this is public information)
        return {'gList': games}


class AIListRequestHandler(GameRouterHandler):
    """Gather & send list of AI modules to client."""
    # Overridden member
    def respond(self, msg):

        if msg.data['ai'] != '0':
            # For now, '0' is just a request for all AIs & only supported value
            return None

        agents = ai_mgr.get_ai_summary()
        
        return {'aList': agents}


class BidHandler(GameRouterHandler):
    """Handle plays made during game."""
    # Overriden members
    def respond(self, msg):
        game_id, pNum = cm.get_client_info(msg.source)
        target_game = self.router.games[game_id]

        bid_val = int(msg.data['bid'])
        response = target_game.handle_bid(pNum, bid_val)

        if response is False:
            return get_error(ERROR_TYPE.ILLEGAL_BID, bid_val)
        
        try:
            self.announce_msgs_from_game(response, game_id)
        except TypeError:
            return None # handle_bid = None if inactive player tries to bid


class GamePlayHandler(GameRouterHandler):
    """Handle plays made (cards) during game."""
    # Overriden members
    def respond(self, msg):
        # Match client GUID to game id and player number
        game_id, pNum = cm.get_client_info(msg.source)
        target_game = self.router.games[game_id]

        # Pass info to Game to call play processing logic for response
        card_num = int(msg.data['card'])
        response = target_game.handle_card_played(pNum, card_num)

        if response is False:
            decoded = cards.decode(card_num)
            
            # Pass in a tuple of the suit and rank names for the error message
            return get_error(ERROR_TYPE.ILLEGAL_PLAY, 
                              (cards.RANKS_BY_NUM[decoded[0]], 
                               cards.SUITS_BY_NUM[decoded[1]])
                            )

        try:
            self.announce_msgs_from_game(response, game_id)
        except TypeError:   # handle_card_played = None when
            return None     #   inactive player tries to play
   

def get_error(err, *args):
    """Create error dict for POST-response.

    error_id (int): constant int defined in ERROR_TYPE
    args (variant): variables used for descriptive error messages
       
    """
    try:
        if err == ERROR_TYPE.FULL_GAME:
            err_val = "Game is full."
        elif err == ERROR_TYPE.INVALID_SEAT:
            err_val = "Seat #{0} is not a valid choice.".format(args[0])
        elif err == ERROR_TYPE.OCCUPIED_SEAT:
            err_val = "Seat #{0} is already occupied.".format(args[0])
        elif err == ERROR_TYPE.ILLEGAL_BID:
            err_val = "Your bid of {0} is illegal.".format(args[0])
        elif err == ERROR_TYPE.ILLEGAL_PLAY:
            err_val = "Your play of the {0} of {1} is illegal.".format(
                        args[0][0], args[0][1])
        else:
            err_val = "Unspecified error type."

    except IndexError:
        # Argument missing from args
        log.exception("get_error_string: Need more args for error_id {0}."
                "".format(error_id))

    return {'err': err_val}
