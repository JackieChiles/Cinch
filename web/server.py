#!/usr/bin/python2
"""Web server component for Cinch.

Classes:

Room -- Container for users and a Cinch game
GameNamespace -- Socket.io namespace for all comms
Server -- Manager for Socket.io connections

Methods:

runServer -- starts Socket.io server

(Room)
isFull
getAvailableSeats
startGame

(GameNamespace)
recv_connect
recv_disconnect
on_test
on_chat
on_createRoom
on_exit
on_join
on_aiList
on_aiListData
on_summonAI
on_bid
on_play
emit_to_room
emit_to_room_not_me
emit_to_another_room
getUsernamesInRoom
getSeatingChart

Implements a Socket.io server and handles all client-server message routing.

"""
# Applies gevent magic to standard sockets
from gevent import monkey; monkey.patch_all()

# This is where the websocket magic comes from
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

from time import sleep
from threading import Timer

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
        self.started = False # flag if a game has been started in this room
    
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
        seats = list(range(0, MAX_ROOM_SIZE))

        # Seats in Lobby can hold any number of people
        if self.num == LOBBY:
            return seats

        for sock in self.users:
            if 'seat' in sock.session:
                try:
                    seats.remove(sock.session['seat'])
                except:
                    print "%d not in available seats" % sock.session['seat']
        
        return seats
    
    def startGame(self):
        """Perform final player checks and start game."""       
        sock = self.users[0] # Need to get reference to the socket namespace

        # Prevent game from restarting if a full room empties and refills
        if self.started:
            sock['/cinch'].emit_to_room('chat', ['System',
                "This game already started, so I won't start a new one."])
            return

        # Ensure all seats filled
        if len(self.getAvailableSeats()) > 0:
            # Something has gone wrong
            log.error("bad seating error in startGame()")
            sock['/cinch'].emit_to_room('err', 'Problem starting game')
            return

        #Send out the final seat chart
        sock['/cinch'].emit_to_room('seatChart', sock['/cinch'].getSeatingChart(sock['/cinch'].session['room']))

        self.game = Game()
        initData = self.game.start_game(sock['/cinch'].getUsernamesInRoom(self))
        
        # Send initial game data to players
        log.debug("Sending initial game data in room %s", self.num)
        for msg in initData:
            # msg['tgt'] is a list. for this msg, it's one-element
            tgt = msg.pop('tgt')[0]
            for sock in self.users:
                if sock.session['seat'] == tgt:
                    sock['/cinch'].emit('startData', msg)
                    break

        self.started = True


class GameNamespace(BaseNamespace, BroadcastMixin):

    """Namespace for all Cinch client-server communications using Socket.io.
    
    Extends socketio.namespace.BaseNamespace and socketio.mixins.BroadcastMixin.
    
    """
    
    # Unhandled exceptions caused by client input won't kill the server as a whole,
    # but will kill that connection. A page refresh seems to be required.
    
    def recv_connect(self):
        """Initialize connection for a client to this namespace.
        
        This gets called when the client first connects (as long as this
        namespace is not the Global namespace ''). A default nickname is assigned
        and the client is moved to the Lobby. Finally, the client is sent a list
        of available rooms.
        
        """
        self.session['nickname'] = 'NewUser'
        
        self.on_join(LOBBY, 0) # Join lobby
        roomList = [{'name': str(x), 'num':x.num, 'isFull': x.isFull(), 
                     'seatChart': self.getSeatingChart(x)}
                    for x in self.request['rooms']]
        del roomList[0] # Don't send lobby
        self.emit('rooms', roomList)

    def recv_disconnect(self):
        """Close the socket connection when the client requests a disconnect."""
        self.on_exit(0) # Remove user from its current room
        self.on_exit(0) # Remove user from lobby

        self.disconnect(silent=True)

    def on_test(self, *args):
        # Dummy command to get the console __init__ to fire.
        log.info('Console connected.')
        return ['ok']
            
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
        """Create new room and announce new room's existence to clients.
        
        args -- {seat: ai_model_id, seat2: ...}
        
        """
        # 'rooms' is list of Room objects
        roomNum = self.request['curMaxRoomNum'] + 1
        newRoom = Room(roomNum)
        self.request['curMaxRoomNum'] += 1

        self.request['rooms'].append(newRoom)     # store new room in Server
        
        # Goes to all clients in Lobby
        self.emit_to_another_room(LOBBY, 'newRoom', {'name': str(newRoom), 
                                                     'num': roomNum, 
                                                     'isFull': newRoom.isFull(),
                                                     'seatChart':[]})
        
        # Summon AI players
        try:
            for seat in args.keys():
                self.emit_to_room('summonAI', {roomNum: (int(seat), int(args[seat]))})
        except AttributeError as e:
            pass # No args given

        return (roomNum, ) # Tells user to join room

        # FUTURE add way to system to add AIs after creating room; useful for filling
        # a room that won't fill. Would be separate command from createRoom.
    
    def on_exit(self, _):
        """Leave room and return to lobby, while announcing to rest of room."""
        curRoom = self.session['room']
        retVal =  ({'seatChart': self.getSeatingChart(curRoom)},)

        if self.socket not in curRoom.users:
            # This user is no longer in this room, so do nothing
            return retVal

        # If user is in the lobby, don't need to do anything
        if curRoom.num == LOBBY:
            return retVal

        try:
            seatNum = self.session['seat']
        except:
            seatNum = -1

        self.emit_to_room_not_me('exit', self.session['nickname'], 
                                 curRoom.num, seatNum)
        self.emit_to_another_room(LOBBY, 'exit', self.session['nickname'], 
                                 curRoom.num, seatNum)

        # When exit fires on disconnect, this may fail, so try-except
        try:
            # If room is full before user leaves, tell Lobby room is not full
            if self.session['room'].isFull():
                self.emit_to_room('roomNotFull', self.session['room'].num)
                self.emit_to_another_room(LOBBY, 'roomNotFull', 
                                          self.session['room'].num)
            
            # Remove user from room
            self.session['room'].users.remove(self.socket)
            
            # If room is now empty, remove the room and notify clients
            # NOTE: this doesn't affect the actual room object, only its availability
            # to clients; this may be a memory leak.
            if len(curRoom.users) == 0 and curRoom.num != LOBBY: # Don't delete Lobby
                self.request['rooms'].remove(curRoom)
                self.broadcast_event('roomGone', curRoom.num)

            # Delete user's seat so it doesn't get carried into the next room
            try:
                del self.session['seat']
            except:
                pass
        
            log.debug('%s left room %s; placing in lobby.',
                      self.session['nickname'], self.session['room'].num)
            self.on_join(LOBBY, 0)

        except:
            pass

        # If lobby successfully joined, need to send ack to client.
        # Client won't get callback from server-emitted on_join.
        return retVal

        #FUTURE do stuff for game-in-progress -- maybe allow player to replace
        #one who left

    def on_join(self, roomNum, seatNum):
        """Join room specified by roomNum.
        
        roomNum -- index in request[rooms] for target room
        seatNum -- (int) target seat number
        
        Client should not allow moving directly from one room to another without
        returning to the lobby. That's done by leaving the room (on_exit), which
        automatically takes you to the lobby. Only then should new joins be allowed.         
        """   
        roomNum = int(roomNum) # sent as unicode from browser
        
        # move to room numbered roomNum if it exists
        try:
            # Set local ref to room
            room = [x for x in self.request['rooms'] if x.num == roomNum][0]

            if room.isFull():
                self.emit('err', 'That room is full')
                return []
            else:
                try:
                    self.on_exit(0) # Leave current room if we're in a room
                except KeyError: # No 'room' key in self.session at start of session
                    pass

                # Verify target seat is available
                if seatNum not in room.getAvailableSeats():
                    self.emit('err', 'That seat is not available')
                    return []
                else:
                    # Add user to room server-side
                    room.users.append(self.socket) # socket includes session field
                    self.session['seat'] = seatNum
                
                self.session['room'] = room     # Record room pointer in session

                # Tell others in room and lobby that someone has joined and sat down
                self.emit_to_room_not_me('enter', self.session['nickname'], 
                                         roomNum, seatNum)
                self.emit_to_another_room(LOBBY, 'enter', self.session['nickname'], 
                                          roomNum, seatNum)
                
                # If the room is now full, begin the game
                # client may want to block/delay ability to leave room at this point
                if room.isFull():
                    self.emit_to_room('roomFull', roomNum)
                    self.emit_to_another_room(LOBBY, 'roomFull', roomNum)

                    # Without this Timer, the last person to join will receive
                    # start data before room data and will not have confirmed
                    # their seat/pNum.
                    t = Timer(0.5, room.startGame)
                    t.start()

                seatChart = self.getSeatingChart(room)

                return ({'roomNum': roomNum, 'seatChart': seatChart, 
                         'mySeat': seatNum},)

        except IndexError:
            self.emit('err', "Room %s does not exist" % roomNum)
            return []

    def on_nickname(self, name):
        """Set nickname for user.
        
        name -- desired nickname
        
        The nickname cannot be changed while the user is in a room other than
        the lobby. This is to protect the integrity of any game logging done.
        
        """
        if self.session['room'].num != LOBBY:  # if room is not Lobby
            self.emit('err', 'You cannot change names while in a game')
            return (None,)
        else:
            # set nickname for user
            self.session['nickname'] = name
            return (name,)

    # --------------------
    # AI methods
    # --------------------
    
    def on_aiList(self, *args):
        """Provide client with list of available AIs and their information."""
        if self.session['room'].num == LOBBY:
            self.emit_to_room('getAIList', None)

            sleep(0.25)  # Brief pause for AI manager to respond
            self.emit('aiInfo', self.request['aiListData'])

    def on_aiListData(self, msg):
        """Receive AI identity information from AI manager."""
        self.request['aiListData'] = msg

    def on_summonAI(self, *args):
        """Human client has requested an AI agent for a game room."""
        log.debug("AI model {0} summoned".format(args[0]['id']))
        
    # --------------------
    # Game methods
    # --------------------

    def on_bid(self, bid):
        """Pass bid to game."""
        g = self.session['room'].game

        if 'seat' in self.session:
            pNum = self.session['seat']
        else:
            #Handle clients bidding while not seated.            
            self.emit('err', 'No seat assigned; bidding not allowed.')
            log.warning('Non-seated client "%s" sent bid %s',
                        self.session['nickname'], bid)
            return

        res = g.handle_bid(pNum, int(bid))
        
        if res is False:
            self.emit('err', 'Bad bid') #False on bad bid, None for inactive player
        elif res is None:
            self.emit('err', "It's not your turn")
        else:
            self.emit_to_room('bid', res)
        
    def on_play(self, play):
        """Pass play to game."""
        g = self.session['room'].game
        
        if 'seat' in self.session:
            pNum = self.session['seat']
        else:
            #Handle clients playing while not seated.
            self.emit('err', 'No seat assigned; playing not allowed.')
            log.warning('Non-seated client "%s" sent play %s',
                        self.session['nickname'], play)
            return

        res = g.handle_card_played(pNum, int(play))
        #False on bad play, None for inactive player

        if res is False:
            log.debug("on_play: illegal play attempted in seat " + str(pNum))
            self.emit('err', 'Bad play')
        elif res is None:
            self.emit('err', "It's not your turn")
        else:
            # TODO implement better way of sending private messages
            if len(res) > 1: # Multiple messages == distinct messages
                for msg in res:
                    tgt = msg['tgt'][0] # Assuming one target per message here
                    for sock in self.session['room'].users:
                        if sock.session['seat'] == tgt:
                            sock['/cinch'].emit('play', [msg])
            else:
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

    def emit_to_another_room(self, roomNum, event, *args):
        """Send message to all users in a room identified by roomNum.

        roomNum -- room number of target room; can be LOBBY
        event -- command name for message (e.g. 'chat', 'users', 'ack')
        args -- args for command specified by event

        """
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        try:
            room = [x for x in self.request['rooms'] if x.num == roomNum][0]
        except IndexError:
            log.warning(str(roomNum) + ' is not a valid room number.')
            return
        
        for sessid, socket in self.socket.server.sockets.iteritems():
            if 'room' not in socket.session:
                continue
            elif socket.session['room'] == room:
                socket.send_packet(pkt)        

    def getUsernamesInRoom(self, room):
        """Return list of all users' nicknames in a given room
        
        room -- Room object
        
        """
        names = []
        for sock in room.users:
            names.append(sock.session['nickname'])
        
        return names

    def getSeatingChart(self, room):
        """Returns a list of (username, seat) pairs for a given room.

        room -- Room object

        If a user does not have a seat, they are given seat = -1.

        """
        seatChart = []
        for sock in room.users:
            name = sock.session['nickname']
            if 'seat' not in sock.session:
                seat = -1
            else:
                seat = sock.session['seat']

            seatChart.append((name, seat))

        return seatChart


class Server(object):

    """Manages namespaces and connections while holding server-global info."""

    # Server-global dict object available to every connection
    request = {'rooms':[Room(LOBBY)], 'curMaxRoomNum': LOBBY, 'aiInfo':dict() } # Room 0:Lobby
    
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
