# chat server with lobby and multiple rooms

# Applies gevent magic to standard sockets
from gevent import monkey; monkey.patch_all()

# This is where the websocket magic comes from
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import RoomsMixin, BroadcastMixin


# Container class for a Room, in which a game will appear
class Room(object):
    game = None     # game object
    users = []      # users in room
    num = 0         # room number
    
    # Move this to constants area
    MAX_ROOM_SIZE = 4
    
    def __init__(self, roomNum):
        self.num = roomNum
    
    def isFull(self):
        if len(users) == MAX_ROOM_SIZE:
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
        self.disconnect(silent=True)
        
    # TODO need function to be called when client estabs socket connection
    # On client, can confirm connection by checking 'socket.socket.connected == true'
    # then emitting an arbitrary message. send room list then instead of on_nickname?
    def __init__(self, *args, **kwargs):
        super(GameNamespace, self).__init__(*args, **kwargs)
        self.session['room'] = ''
        self.emit('rooms', self.request['rooms'])
        
    def on_nickname(self, name):
        # TODO should limit this to being invoked from the lobby -- don't want to 
        # deal with name changes mid-game
        
        # set nickname for user
        self.session['nickname'] = name
        self.emit('ackNickname', name)  # ack nickname okay (could do collision checking here)
        self.emit('rooms', self.request['rooms'])
    
    def on_chat(self, message):
        # broadcast chat message to room
        if 'nickname' in self.session:
            self.emit_to_room('chat', [self.session['nickname'], message])
        else:
            self.emit('err', 'You must set a nickname first')
    
    def on_exit(self, whatever):
        # leave room and return to lobby
        self.emit_to_room_not_me('exit', self.session['nickname'])
         #FUTURE do stuff for game-in-progress -- maybe allow player to replace
        #one who left
               
    def on_createRoom(self, message):
        roomNum = len(self.request['rooms'])    # rooms is global list of Room objects
        newRoom = Room(roomNum)
        
        newRoom.users.append(self.socket) # useful, but may lack session info (check this)

        self.request['rooms'].append(newRoom)       # Store new room in Server
        
        # TODO instead broadcast only to lobby; requires players being auto-
        # entered into lobby upon connection -- currently they are not
        self.broadcast_event('newRoom', roomNum)   # goes to all-all clients
        
        self.emit('ackCreate', roomNum)    # tell user to join the room
    
    def on_join(self, roomNum):
        # move to room named roomName if it exists
        if roomNum not in range(0, len(self.request['rooms'])):
            self.emit('err', "%i does not exist" % roomNum)
        else:  
            # Set local ref to room
            self.session['room'] = self.request['rooms'][roomNum]
            self.emit('ackJoin', roomNum)      # tell client okay

            # Get list of usernames in room
            self.emit('users', [])  # TODO track users in room server-side
            
            # tell others in room that someone has joined
            self.emit_to_room_not_me('enter', self.session['nickname'])

    def on_exec(self, message):
        # Debugging helper - client sends arbitrary Python code for execution
        # From the client browser console, type:
        # socket.emit('exec', <your Python code>)
        # Please be careful.
        #
        # TODO remove this method before it goes live
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

    
# This might should live in a separate file and be imported here. Can break this
# file up later.
class Server(object):
    request = {'rooms':[None] } # None is placeholder for Room 0:Lobby
    
    def __call__(self, environ, start_response):
        path = environ['PATH_INFO'].strip('/')

        if path.startswith("socket.io"):
            socketio_manage(environ, 
                {'': GameNamespace}, self.request)
        else:
            print "not found ", path


def runServer():
    print 'Listening on port 8088 and on port 10843 (flash policy server)'
    SocketIOServer(('0.0.0.0', 8088), Server(),
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
