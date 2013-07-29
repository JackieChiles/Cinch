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
from socketio.mixins import RoomsMixin, BroadcastMixin


# Constants
LOBBY = 0
MAX_ROOM_SIZE = 4


class Room(object):

    """Container class for a game and users, in which a game will appear."""
    
    def __init__(self, roomNum):
        """Create a new Room with a given room number.
        
        roomNum -- the specified room number, used for descriptive purposes only.
        
        """
        self.num = roomNum
        self.game = None     # game object
        self.users = []      # users in room
    
    def __str__(self):
        """Return a label for the room, with special handling for the Lobby."""
        if self.num == LOBBY:
            return "Lobby"
        else:
            return "Game %i" % self.num
    
    def isFull(self):
        """Check if the room is full and return a boolean. Lobby cannot fill up."""
        if self.num == LOBBY: # Lobby never fills
            return False
        elif len(self.users) == MAX_ROOM_SIZE:
            return True
        else:
            return False


class GameNamespace(BaseNamespace, BroadcastMixin):

    """Namespace for all Cinch client-server communications using Socket.io.

    """
    
    # Unhandled exceptions caused by client input won't kill the server as a whole,
    # but will kill that connection. A page refresh seems to be required.
    
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
            print e
            
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
            
    def on_createRoom(self, _):
        """Create new room and announce new room's existance to clients.
        
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
    
    def on_exit(self, _):
        """Leave room and return to lobby, while announcing to rest of room."""
        self.emit_to_room_not_me('exit', self.session['nickname'])
        
        # When exit fires on disconnect, this may fail, so try-except
        try:
            self.session['room'].users.remove(self.socket)
        
            if self.session['room'].num != LOBBY:   # Don't rejoin lobby if leaving lobby
                self.on_join(LOBBY)
        except:
            pass
            
        #FUTURE do stuff for game-in-progress -- maybe allow player to replace
        #one who left
    
    def on_join(self, roomNum):
        """Join room specified by roomNum.
        
        roomNum -- index in request[rooms] for target room
        
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
                
                self.emit('ackJoin', roomNum)      # tell client okay

                # Send list of usernames in room
                self.emit('users', self.getUsernamesInRoom(room))
                
                # tell others in room that someone has joined
                self.emit_to_room_not_me('enter', self.session['nickname'])

    def on_nickname(self, name):
        """Set nickname for user and announce.
        
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
            self.emit('rooms', [str(x) for x in self.request['rooms']])

    # --------------------
    # Game & game routing methods
    # --------------------
            
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
    SocketIOServer(('0.0.0.0', 8088), Server(),
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
