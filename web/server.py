# chat server with lobby and multiple rooms

# Unhandled exceptions caused by client input won't kill the server as a whole,
# but will kill that connection. A page refresh seems to be required.

# Applies gevent magic to standard sockets
from gevent import monkey; monkey.patch_all()

# This is where the websocket magic comes from
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin


LOBBY = 0
MAX_ROOM_SIZE = 4

# Container class for a Room, in which a game will appear
class Room(object):
    def __init__(self, roomNum):
        self.num = roomNum
        self.game = None     # game object
        self.users = []      # users in room
    
    def __str__(self):
        if self.num == LOBBY:
            return "Lobby"
        else:
            return "Game %i" % self.num
    
    def isFull(self):
        if self.num == LOBBY: # Lobby never fills
            return False
        elif len(self.users) == MAX_ROOM_SIZE:
            return True
        else:
            return False


# Namespace object can share class-level information among connections
# Namespace.session is private to a connection
class GameNamespace(BaseNamespace, BroadcastMixin):
    # Handlers
    def recv_disconnect(self):
        # remove user from room & send disconnect message
        # finish by calling disconnect method
        self.on_exit(0)      
        self.disconnect(silent=True)
        
    # This gets called when client connects, so long as this isn't the Global namespace
    # FUTURE investigate how reconnects are handled wrt calling this method.
    def __init__(self, *args, **kwargs):
        super(GameNamespace, self).__init__(*args, **kwargs)
        self.session['nickname'] = 'NewUser'
        
        self.on_join(LOBBY) # Join lobby
        self.emit('rooms', [str(x) for x in self.request['rooms']])
        
    def on_nickname(self, name):
        if self.session['room'].num != LOBBY:  # if room is not Lobby
            self.emit('err', 'You cannot change names while in a game')
        else:
            # set nickname for user
            self.session['nickname'] = name
            self.emit('ackNickname', name)  # ack nickname okay (could do collision checking here)
            self.emit('rooms', [str(x) for x in self.request['rooms']])
    
    def on_chat(self, message):
        # broadcast chat message to room
        # If client wants to change the output formatting for own messages, let
        # the client do it -- just compare the nicknames.
        if 'nickname' in self.session:
            self.emit_to_room('chat', [self.session['nickname'], message])
        else:
            self.emit('err', 'You must set a nickname first')
    
    def on_exit(self, _):
        # leave room and return to lobby
        self.emit_to_room_not_me('exit', self.session['nickname'])
        
        # When exit fires on disconnect, this may fail, so try-except
        try:
            self.session['room'].users.remove(self.socket)
        
            if self.session['room'].num != LOBBY:   # Don't rejoin lobby if leaving lobby
                self.on_join(LOBBY) # Enter lobby
        
        except:
            pass
            
        #FUTURE do stuff for game-in-progress -- maybe allow player to replace
        #one who left
               
    def on_createRoom(self, message):
        roomNum = len(self.request['rooms'])    # rooms is global list of Room objects
        newRoom = Room(roomNum)

        self.request['rooms'].append(newRoom)       # Store new room in Server
        
        # TODO broadcast only to lobby
        self.broadcast_event('newRoom', roomNum)   # goes to all-all clients
        
        self.emit('ackCreate', roomNum)    # tell user to join the room
    
    def on_join(self, roomNum):
        # Client should not allow moving directly from one room to another without
        # returning to the lobby. That's done by leaving the room (on_exit), which
        # automatically takes you to the lobby. Only then should new joins be allowed.     
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


    # --------
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
    # Helper methods
    # --------------------    
    def emit_to_room_not_me(self, event, *args):
        # Modified form of version in RoomsMixIn
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

    def emit_to_room(self, event, *args):
        # Modified form of version in RoomsMixIn
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        room = self.session['room']
        
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'room' not in socket.session:
                continue
            elif socket.session['room'] == room:
                socket.send_packet(pkt)    

    def getUsernamesInRoom(self, room):
        names = []
        for sock in room.users:
            names.append(sock.session['nickname'])
        
        return names
        
        
    
# This might should live in a separate file and be imported here. Can break this
# file up later.
class Server(object):
    request = {'rooms':[Room(LOBBY)] } # Room 0:Lobby
    
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO'].strip('/')

        if path.startswith("socket.io"):
            socketio_manage(environ, {'/cinch': GameNamespace}, self.request)
        else:
            print "not found ", path


def runServer():
    print 'Listening on port 8088 and on port 10843 (flash policy server)'
    SocketIOServer(('0.0.0.0', 8088), Server(),
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
