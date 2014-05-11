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

from time import sleep

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
                    # changing the namespace name will break this; TODO use variable
            
            if len(self.getAvailableSeats()) > 0:
                # Something has gone wrong
                log.error("bad seating error in startGame()")
                sock['/cinch'].emit_to_room('err', 'Problem starting game')
                return

        #Send out the final seat chart
        sock['/cinch'].emit_to_room('seatChart', sock['/cinch'].getSeatingChart(sock['/cinch'].session['room']))

        #FIXME if players leave then rejoin, a new game is started.
        self.game = Game()
        initData = self.game.start_game(self.users[0]['/cinch'].getUsernamesInRoom(self))
        
        # Send initial game data to players
        for msg in initData:
            # msg['tgt'] is a list. for this msg, it's one-element
            tgt = msg.pop('tgt')[0]
            for sock in self.users:
                if sock.session['seat'] == tgt:
                    sock['/cinch'].emit('startData', msg)
                    break


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
        
        TODO: need to accept request for own seat number
        
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
        retVal =  ({'seatChart': 'lobby'},) # TODO send list of ppl in lobby
        curRoom = self.session['room']

        if self.socket not in curRoom.users:
            # This user is no longer in this room, so do nothing
            return retVal

        # If user is in the lobby, don't need to do anything
        if curRoom.num == LOBBY:
            return retVal

        self.emit_to_room_not_me('exit', self.session['nickname'])

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
            else:
                try:
                    self.on_exit(0) # Leave current room if we're in a room
                except KeyError: # No 'room' key in self.session at start of session
                    pass
                
                self.session['room'] = room     # Record room pointer in session
                
                # Add user to room server-side
                room.users.append(self.socket) # socket includes session field            
                # Tell others in room that someone has joined
                self.emit_to_room_not_me('enter', self.session['nickname'])
                
                # if the room is now full, begin the game
                # client may want to block/delay ability to leave room at this point
                if room.isFull():
                    self.emit_to_room('roomFull', roomNum)
                    self.emit_to_another_room(LOBBY, 'roomFull', roomNum)
                    room.startGame()

                if roomNum == 0:
                    seatChart = "lobby"
                else:
                    seatChart = self.getSeatingChart(room)

                # TODO make client handle seatChart; may then remove 'users'
                users = self.getUsernamesInRoom(room) ###
                return ({'roomNum': roomNum, 'seatChart': seatChart, 'users': users},)

        except IndexError:
            self.emit('err', "Room %s does not exist" % roomNum)
            return []

    def on_seat(self, seat):
        """Set seat number in room for user. User cannot change seat once seated.
        
        seat -- seat number
        
        This method sends an 'ack' to confirm that the selected seat was applied.
        
        """
        if 'seat' in self.session: # User already seated; can't change
            #TODO handle this process better pending re-enabling of client-side selection
            self.emit('ackSeat', -1)

        elif seat in self.session['room'].getAvailableSeats():
            self.session['seat'] = seat
            self.emit('ackSeat', seat)
            
            #Announce the seat occupant to all users          
            self.emit_to_room('userInSeat', { 'actor': seat, 'name': self.session['nickname'] })
###            return (seat,) #TODO: Pending re-enabling of client seat selection

        else:
            self.emit('err', 'That seat is already taken. Pick a different one')
###            return (None,)

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
