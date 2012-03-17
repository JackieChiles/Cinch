#!/usr/bin/python3
"""Game router for Cinch.

TODO: add threading/async capes -- mostly handled already by CometServer?


"""
from threading import Timer #for delayed start

# All import paths are relative to the root
import core.common as common
from core.game import Game, NUM_PLAYERS
from web.message import Message
from web.channel import CommChannel

MAX_GAME_SIZE = NUM_PLAYERS # Max number of players in a game
START_GAME_DELAY = 3.0 # Time to wait between last player joining and starting
DEFAULT_PNUM = 0 # pNum assigned to player who creates new game

# Message signatures
SIGNATURE = common.enum(
    NEW_GAME=['game'],
    JOIN_GAME=['join', 'pNum'],
    GAME_PLAY=['card'],
    BID=['bid']
    )

# Enum constants for building POST-response error messages
ERROR_TYPE = common.enum(
    FULL_GAME=1,
    INVALID_SEAT=2,
    OCCUPIED_SEAT=3,
    ILLEGAL_BID=4,
    ILLEGAL_PLAY=5
    )

# Global variable
cm = None   # Used for client manager


class GameRouter:
    """Manage handlers for traffic between games and clients."""
    def __init__(self):
        self.games = dict() # key=game_id, value=game object
        self.handlers = []

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
        
        # Create action handlers
        self.handlers.append(NewGameHandler(self, SIGNATURE.NEW_GAME))
        self.handlers.append(JoinGameHandler(self, SIGNATURE.JOIN_GAME))        
        self.handlers.append(GamePlayHandler(self, SIGNATURE.GAME_PLAY))
        self.handlers.append(BidHandler(self, SIGNATURE.BID))

        # Register each handler with the Comet server
        for h in self.handlers:
            h.register(server)
            
    def get_client_guids(self, guid):
        return cm.get_clients_in_group(cm.get_group_by_client(guid))


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

    def register(self, server):
        """
        server (CometServer): reference to web server
        """
        server.add_responder(self, self.signature)
        server.add_announcer(self)

    def announce_msgs_from_game(self, msg_list, game_id):
        """Build Messages from Game and announce to web server."""
        #TODO: if the message for multiple clients is the same,
        #       combine the destinations into one message
        outgoing_msgs = []
        
        for element in msg_list:
            dest_pNum = element.pop('tgt')

            # Convert pNum to uid
            dest = cm.get_client_by_player_num(game_id, dest_pNum)
            outgoing_msgs.append(
                Message(element, source=game_id, dest_list=[dest]))
    
        # Announce each message
        for x in outgoing_msgs:  self.announce(x)


#--------------------
# Handlers for specific message types / actions
#--------------------
class NewGameHandler(GameRouterHandler):
    """React to New Game requests from server."""
    # Overriden member
    def respond(self, msg):
        
        if msg.data['game'] != '0':
            # May support other types of game requests in the future
            return None

        ######
        # FUTURE: Set limit on # concurrent games and enforce limit here.
        #       Will make use of thread pool (where?); pool size = limit.
        ######
        
        # Create new game object and add to router.games and client_mgr
        new_game = Game()
        game_id = cm.create_group()
        self.router.games[game_id] = new_game
        
        # Create GUID for requesting client and add entry to client_mgr
        client_id = cm.create_client(pNum=DEFAULT_PNUM)
        cm.add_client_to_group(client_id, game_id)

        # Return client GUID and player number via POST
        return {'uid': client_id, 'pNum': DEFAULT_PNUM}


class JoinGameHandler(GameRouterHandler):  ###untested
    """React to client requests to join a game."""
    # Overriden member
    def respond(self, msg):
        # TODO: inhibit join request if game started; need flag in Game
        
############## delete following block when following block becomes enabled

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
        except IndexError:
            return get_error(ERROR_TYPE.FULL_GAME)

############## delete preceeding block when following block becomes enabled

##        ############## untested
##        # TODO: uncomment this block once client allows players to select seat
##        #############
##        
##        # Check if requested seat is a valid seat
##        requested_pNum = int(msg.data['pNum'])
##        poss_nums = [x for x in range(0, MAX_GAME_SIZE)]
##        if requested_pNum not in poss_nums:
##            return get_error(ERROR_TYPE.INVALID_SEAT, requested_pNum)
##
##        # Get list of currently occupied seats in target game
##        game_id = int(msg.data['join'])
##        cur_player_nums = cm.get_player_nums_in_group(game_id)
##
##        # Check if game is full
##        if len(poss_nums) == len(cur_player_nums):
##            return get_error(ERROR_TYPE.FULL_GAME)
##        # Check if requested seat is occupied
##        if requested_pNum in cur_player_nums:
##            return get_error(ERROR_TYPE.OCCUPIED_SEAT, pNum)
##
##        # pNum is valid selection
##        pNum = requested_pNum
##        

        # Create GUID for requesting client and add entry to client_mgr
        client_id = cm.create_client(pNum=pNum)
        cm.add_client_to_group(client_id, game_id)

        # Check if game is now full. If so, trigger and announce game start
        if len(cm.groups[game_id]) == MAX_GAME_SIZE:
            # After short delay (so last client to join can receive uid/pNum
            # response from return statement) start game and send clients
            # game-start info (hands, active player, etc.)
            def launch_game(self, game_id):
                init_data = self.router.games[game_id].start_game()
                self.announce_msgs_from_game(init_data, game_id)
                print("Game Router: game started")

            t = Timer(START_GAME_DELAY, launch_game, args=[self, game_id])
            t.start()

        # Return client GUID and assigned player number
        return {'uid': client_id, 'pNum': pNum}


#####
#TODO: Implement way to drop from game before/after game start
#####


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
            return get_error(ERROR_TYPE.ILLEGAL_PLAY, card_num)

        try:
            self.announce_msgs_from_game(response, game_id)
        except TypeError:   # handle_card_played returns None
            return None     # when inactive player tries to play a card
   

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
            err_val = "Your play of {0} is illegal.".format(args[0])
        else:
            err_val = "Unspecified error type."

    except IndexError:
        # Argument missing from args
        raise RuntimeError("get_error_string: Need more args for error_id {0}."
                           .format(error_id))

    return {'err': err_val}
