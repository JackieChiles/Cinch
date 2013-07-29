# chat server with lobby and multiple rooms

# Applies gevent magic to standard sockets
from gevent import monkey; monkey.patch_all()

# This is where the websocket magic comes from
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin


# Make global things global. It'll be fine.
games = []



# Namespace object can share class-level information among connections
# Namespace.session is private to a connection

class GameNamespace(BaseNamespace, BroadcastMixin):


    # Handlers
    def recv_disconnect(self):
        # remove user from room & send disconnect message
        # finish by calling disconnect method    
        print self.session    
        self.disconnect(silent=True)
        
    # TODO need function to be called when client estabs socket connection
    # send room list then instead of on_nickname
    def __init__(self, *args, **kwargs):
        # __init__ not called until first message sent by client, so need
        # to make client send a message upon connection
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
        # leave game and return to lobby
        self.emit_to_room_not_me('exit', self.session['nickname'])
        #FUTURE do stuff for game-in-progress -- maybe allow player to replace
        #one who left
            
    def on_createGame(self):
        # TODO determine game number from Server
        gameNum = random.randInt(1, 1000)
        
        # create new game & ack client
        self.request['games'].append(gameNum)
        
        # TODO instead broadcast only to lobby; requires players being auto-
        # entered into lobby upon connection -- currently they are not
        self.broadcast_event('newRoom', gameNum)   # goes to all-all clients
        
        self.emit('ackCreate', gameNum)    # tell user to join the game
    
    def on_join(self, gameNum):
        # move game numbered gameNum if it exists
        if gameNum not in self.request['games']:
            self.emit('err', gameNum + " does not exist")
        else:  
            self.session['gameNum'] = gameNum     # set local record of gameNum
            self.emit('ackJoin', gameNum)      # tell client okay
                    
            self.emit('users', [])  # TODO track users in game server-side
            
            # tell others in room that someone has joined
            self.emit_to_room_not_me('enter', self.session['nickname'])


    # --------------------
    # Game handlers
    # --------------------
    


    # --------------------
    # Helper methods
    # --------------------
    def emit_to_game_not_me(self, event, *args):
        # Modified form of version in RoomsMixIn
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        gameNum = self.session['gameNum']
        
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'game' not in socket.session:
                continue
            elif socket.session['gameNum'] == gameNum:
                if socket is self.socket:
                    continue
                else:
                    socket.send_packet(pkt)

    def emit_to_room(self, event, *args):
        # Modified form of version in RoomsMixIn
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        gameNum = self.session['gameNum']
        
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'game' not in socket.session:
                continue
            elif socket.session['gameNum'] == gameNum:
                socket.send_packet(pkt)    

# This might should live in a separate file and be imported here.
class Server(object):
    request = {'games':[], 'gameNums':[] }
    
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
