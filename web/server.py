#!/usr/bin/python2
"""Web server component for Cinch.

Classes:
Room -- Container for users and a Cinch game
GameNamespace -- Socket.io namespace for all comms
Server -- Manager for Socket.io connections

Methods:
runServer -- starts Socket.io server

Implements a Socket.io server and handles all client-server message routing.
Replaces legacy modules ClientManager and GameRouter.

"""
# Applies gevent magic to standard sockets
from gevent import monkey; monkey.patch_all()

# This is where the websocket magic comes from
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

import logging
log = logging.getLogger(__name__)
# TODO make use of logging in code

from core.game import Game, NUM_PLAYERS

# Constants
LOBBY = 0
MAX_ROOM_SIZE = NUM_PLAYERS


class Room(object):

    """Container class for a game and users, in which a game will appear."""
    
    def __init__(self, roomNum):
        """Create a new Room with a given room number.
        
        roomNum -- the specified room number, used for descriptive purposes only.
        
        """
        self.num = roomNum   # room descriptor
        self.game = None     # game object
        self.users = []      # user sockets in room
    
    def __str__(self):
        """Return a label for the room, with special handling for the Lobby."""
        if self.num == LOBBY:
            return "Lobby"
        else:
            return "Room %i" % self.num
    
    def isFull(self):
        """Check if the room is full and return a boolean. Lobby cannot fill up."""
        if self.num == LOBBY: # Lobby never fills
            return False
        elif len(self.users) == MAX_ROOM_SIZE:
            return True
        else:
            return False
    
    def getAvailableSeats(self):
        """Returns list of unoccupied seat numbers in range(0, MAX_ROOM_SIZE)."""
        # TODO consider changing from base-0 to base-1 for pNums
        seats = list(range(0, MAX_ROOM_SIZE))
        
        for sock in self.users:
            if 'seat' in sock.session:
                try:
                    seats.remove(sock.session['seat'])
                except:
                    print "%d not in available seats" % sock.session['seat']
        
        return seats
    
    def startGame(self):
        """Perform final player checks and start game.
        
        If any players are not seated when this is called, they'll be assigned
        seats. It may be preferable to prompt unseated players first, but testing
        is required.
        """       
        # Ensure all seats filled
        availableSeats = self.getAvailableSeats()
        if len(availableSeats) > 0:
            # Some seats are empty, so auto-assign
            for sock in self.users:
                if 'seat' not in sock.session:
                    curSeat = availableSeats.pop() 
                    sock.session['seat'] = curSeat
                    sock['/cinch'].emit('ackSeat', curSeat)
                    # changing the namespace name will break this
            
            if len(self.getAvailableSeats()) > 0:
                # Something has gone wrong
                print "bad seating error in startGame()"
                sock['/cinch'].emit_to_room('err', 'Problem starting game')
                return
                
        self.game = Game()
        initData = self.game.start_game(self.users[0]['/cinch'].getUsernamesInRoom(self))
        
        # Send initial game data to players
        for msg in initData:
            # msg['tgt'] is a list. for this msg, it's one-element
            tgt = msg.pop('tgt')[0]
            for sock in self.users:
                if sock.session['seat'] == tgt:
                    sock['/cinch'].emit('startData', msg)
                    continue              


class GameNamespace(BaseNamespace, BroadcastMixin):

    """Namespace for all Cinch client-server communications using Socket.io.
    
    Extends socketio.namespace.BaseNamespace and socketio.mixins.BroadcastMixin.
    
    TODO add public method list to docstring

    """
    
    # Unhandled exceptions caused by client input won't kill the server as a whole,
    # but will kill that connection. A page refresh seems to be required.
    
    # TODO change this to recv_connect()
    def __init__(self, *args, **kwargs):
        """Initialize connection for a client to this namespace.
        
        This gets called when the client first connects (as long as this
        namespace is not the Global namespace ''). A default nickname is assigned
        and the client is moved to the Lobby. Finally, the client is sent a list
        of available rooms.
        
        """
        super(GameNamespace, self).__init__(*args, **kwargs)
        self.session['nickname'] = 'NewUser'
        
        self.on_join(LOBBY) # Join lobby
        self.emit('rooms', [str(x) for x in self.request['rooms']])

    def recv_disconnect(self):
        """Close the socket connection when the client requests a disconnect."""    
        self.on_exit(0)      # Remove user from its current room
        self.disconnect(silent=True)

    # %%%%%
    def on_exec(self, message):
        # Debugging helper - client sends arbitrary Python code for execution
        # From the client browser console, type:
        # socket.emit('exec', <your Python code>)
        # Please be careful. This is offensively dangerous.
        #
        # remove this method before it goes live
        try:
            exec(message)
        except Exception, e:
            print 'on_exec error: ', e
            
    # --------------------
    # Room & chat management methods
    # --------------------
    
    def on_chat(self, message):
        """Transmit chat message to room, including nickname of sender.

        message -- chat string from client 
        
        If the client desires different formatting for messages that it sent,
        the client should compare its nickname to that of the chat message. The
        server sends the same data to all clients in the room.
        
        """
        if 'nickname' in self.session:
            self.emit_to_room('chat', [self.session['nickname'], message])
        else:
            self.emit('err', 'You must set a nickname first')
            
    def on_createRoom(self, args):
        """Create new room and announce new room's existance to clients.
        
        args -- ? probably AI parameters
        
        This method sends an 'ack' to the client, instructing the client to join
        the room, separating the creation of the room from the act of joining
        it.
        
        """
        roomNum = len(self.request['rooms'])    # rooms is list of Room objects
        newRoom = Room(roomNum)

        self.request['rooms'].append(newRoom)     # store new room in Server
        
        # TODO broadcast only to lobby
        self.broadcast_event('newRoom', roomNum)  # goes to all clients in room
        
        self.emit('ackCreate', roomNum)           # tell user to join the room
        
        # TODO accept AI specifications
        
        # FUTURE add way to system to add AIs after creating room; useful for filling
        # a room that won't fill
    
    def on_exit(self, _):
        """Leave room and return to lobby, while announcing to rest of room."""
        self.emit_to_room_not_me('exit', self.session['nickname'])
        
        # When exit fires on disconnect, this may fail, so try-except
        try:
            # Remove user from room
            self.session['room'].users.remove(self.socket)
            
            # Delete user's seat so it doesn't get carried into the next room
            try:
                del self.session['seat']
            except:
                pass
        
            if self.session['room'].num != LOBBY:   # Don't rejoin lobby if leaving lobby
                self.on_join(LOBBY)
        except:
            pass
            
        #FUTURE do stuff for game-in-progress -- maybe allow player to replace
        #one who left
    
    def on_join(self, roomNum):
        """Join room specified by roomNum.
        
        roomNum -- index in request[rooms] for target room
        
        This method sends an 'ack' to the client, which includes the room number
        for confirmation and a list of available seats for selection. The client
        should prompt the user to select one and emit a 'seat' command.
        
        Client should not allow moving directly from one room to another without
        returning to the lobby. That's done by leaving the room (on_exit), which
        automatically takes you to the lobby. Only then should new joins be allowed.          
        
        """   
        roomNum = int(roomNum) # sent as unicode from browser
        
        # move to room numbered roomNum if it exists
        if roomNum not in range(0, len(self.request['rooms'])):
            # Simply using index of room in request['rooms'] for now. When we
            # decide to have completed games be deleted, we'll need a different
            # data structure and an update to this block.
            self.emit('err', "%s does not exist" % roomNum)
        else:  
            # Set local ref to room
            room = self.request['rooms'][roomNum]
            
            if room.isFull():
                self.emit('err', 'That room is full')
            else:
                if 'room' in self.session:
                    self.on_exit(0) # Leave current room if we're in a room
                                    # (won't be in a room at start of connection)
                
                self.session['room'] = room     # Record room pointer in session
                
                # Add user to room server-side
                room.users.append(self.socket) # socket includes session field            
                
                # Confirm join to client & provide list of available seats
                if roomNum == 0:
                    self.emit('ackJoin', (0, 'lobby'))
                else:
                    seats = room.getAvailableSeats()
                    self.emit('ackJoin', (roomNum, seats))

                # Send list of usernames in room
                self.emit('users', self.getUsernamesInRoom(room))
                
                # tell others in room that someone has joined
                self.emit_to_room_not_me('enter', self.session['nickname'])
                
                # if the room is now full, begin the game
                # client may want to inhibit/delay ability to leave room at this point
                if room.isFull():
                    self.emit_to_room('roomFull', '')
                    room.startGame()

    def on_seat(self, seat):
        """Set seat number in room for user.
        
        seat -- seat number
        
        This method sends an 'ack' to confirm that the selected seat was applied.
        
        """
        if seat in self.session['room'].getAvailableSeats():
            self.session['seat'] = seat
            self.emit('ackSeat', seat)
        else:
            self.emit('err', 'That seat is already taken. Pick a different one')

    def on_nickname(self, name):
        """Set nickname for user.
        
        name -- desired nickname
        
        This method sends an 'ack' to the client to confirm the request and
        instruct it to update its local copy of the nickname. This is to allow
        the server to prevent duplicate nicknames (TODO).
        
        The nickname cannot be changed while the user is in a room other than
        the lobby. This is to protect the integrity of any game logging done.
        
        """
        if self.session['room'].num != LOBBY:  # if room is not Lobby
            self.emit('err', 'You cannot change names while in a game')
        else:
            # set nickname for user
            self.session['nickname'] = name
            self.emit('ackNickname', name)  # ack nickname okay

    # --------------------
    # Game methods
    # --------------------
    
    # TODO add AI management methods (e.g. add AI to game). At the moment, all AI
    # is disabled pending web server overhaul and revamp of multiprocessing.
    
    # Could emit acks to sending client and emit_to_room_not_me the rest if that
    # is beneficial.
    
    def on_aiList(self, _):
        """Provide client with list of available AIs and their information."""
        pass
        
    def on_bid(self, bid):
        """Pass bid to game."""
        g = self.session['room'].game
        pNum = self.session['seat']
        
        res = g.handle_bid(pNum, int(bid))
        
        if res is False:
            self.emit('err', 'Bad bid') #False on bad bid, None for inactive player
        else:
            self.emit_to_room('bid', res)
        
    def on_play(self, play):
        """Pass play to game."""
        g = self.session['room'].game
        pNum = self.session['seat']
        
        res = g.handle_card_played(pNum, int(play)) #False on bad play, None for inactive player
        
        if res is False:
            self.emit('err', 'Bad play')
        else:
           # if 'addC' in res: # Private information, so handle differently
           #     pass #TODO
           # else:
           #     self.emit_to_room('play', res)
            
            self.emit_to_room('play', res)
                  
            
    # --------------------
    # Helper methods
    # --------------------

    def emit_to_room(self, event, *args):
        """Send message to all users in sender's room.

        event -- command name for message (e.g. 'chat', 'users', 'ack')
        args -- args for command specified by event
        
        This is a modified form of the same-name method in 
        socketio.mixins.RoomsMixIn, adapted for our concept of a Room.
        
        """
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        room = self.session['room']
        
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'room' not in socket.session:
                continue
            elif socket.session['room'] == room:
                socket.send_packet(pkt)   
     
    def emit_to_room_not_me(self, event, *args):
        """Send message to all users in sender's room except sender itself.
        
        event -- command name for message (e.g. 'chat', 'users', 'ack')
        args -- args for command specified by event
        
        This is a modified form of the same-name method in 
        socketio.mixins.RoomsMixIn, adapted for our concept of a Room.
        
        """
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        room = self.session['room']
        
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'room' not in socket.session:
                continue
            elif socket.session['room'] == room:
                if socket is self.socket:
                    continue
                else:
                    socket.send_packet(pkt)

    def getUsernamesInRoom(self, room):
        """Return list of all users' nicknames in a given room
        
        room -- Room object
        
        """
        names = []
        for sock in room.users:
            names.append(sock.session['nickname'])
        
        return names
        
    
# This might should live in a separate file and be imported here. Can break this
# file up later.
class Server(object):

    """Manages namespaces and connections while holding server-global info."""

    # Server-global dict object available to every connection
    request = {'rooms':[Room(LOBBY)] } # Room 0:Lobby
    
    def __call__(self, environ, start_response):
        """Delegate incoming message to appropriate namespace."""
        path = environ['PATH_INFO'].strip('/')

        if path.startswith("socket.io"):
            # Client should socket connect on 'http://whatever:port/cinch'
            socketio_manage(environ, {'/cinch': GameNamespace}, self.request)
        else:
            print "not found ", path


def runServer():
    """Start socketio server on ports specified below."""
    print 'Listening on port 8088 and on port 10843 (flash policy server)'
    
    try:
        SocketIOServer(('0.0.0.0', 8088), Server(),
            resource="socket.io", policy_server=True,
            policy_listener=('0.0.0.0', 10843)).serve_forever()
    except KeyboardInterrupt:
        print 'Server halted with keyboard interrupt'
    except Exception, e:
        raise e
