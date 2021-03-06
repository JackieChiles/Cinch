#!/usr/bin/python2

"""SocketIO server for Cinch.

This handles all game communications via a socketio interface. Both web clients
and local entities (AIs, command console) connect through this interface. The
server sends and receives socketio events and routes traffic to game rooms
and clients as needed.

This does not serve static files like web pages and JS files. Cinch must be
hosted with a traditional web server (e.g. Apache).

Attributes:
  log (Logger): Log interface common to all Cinch modules.
  LOBBY (int): Room number for Lobby.
  MAX_ROOM_SIZE (int): Maximum number of players allowed in a room, not
    including the Lobby.

Public classes:
  Room: Organizes groups of clients with their corresponding Game object.
  GameNamespace: SocketIO namespace used by server.
  Server: Manager for SocketIO connections.

Public methods:
  runServer: Starts SocketIO server. Blocks main thread.

"""

# Applies gevent magic to standard sockets
from gevent import monkey
monkey.patch_all()

# This is where the websocket magic comes from
from socketio import socketio_manage
from socketio.server import SocketIOServer
from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

from threading import Timer

import logging
log = logging.getLogger(__name__)

from db import parseLog
from core.game import Game, NUM_PLAYERS
from common import SOCKETIO_PORT, SOCKETIO_NS, db

# Constants
LOBBY = 0
MAX_ROOM_SIZE = NUM_PLAYERS


class Room(object):
    """Container class for a game and users.

    To improve data management, a Room does not directly reference players.
    Instead, each player (socket connection) keeps their room number in their
    session and the Room object is located on-demand. This normalizes the data
    relationship and keeps the Room from maintaining an internal player list
    that could get out of sync with reality.

    Attributes:
      server (Server): Pointer to active server object.
      num (int): The room ID number.
      game (core.game Game): Game object.
      users (list of sockets): The users in the room.
      started (boolean): If a game has been started in this room.

    """
    server = None

    def __init__(self, roomNum):
        """Create a new Room with a given room number.

        Args:
          roomNum (int): The specified room number for identification purposes.

        """
        self.num = roomNum
        self.game = None
        self.started = False

    def __str__(self):
        """Return a label for the room, with special handling for the Lobby."""
        if self.num == LOBBY:
            return "Lobby"
        else:
            return "Room %i" % self.num

    def __del__(self):
        """Safely delete the Room."""
        log.debug("TODO: safely end game.")

    def getUsers(self):
        """Return list of sockets for clients in this room."""
        return [x for x in self.server.sockets.values()
                if 'roomNum' in x.session and x.session['roomNum'] == self.num]

    def getUsernamesInRoom(self):
        """Return list of all users' nicknames in this room.

        This method ensures the names are in seat order. If we implement
        username listing for the lobby, this will have to be modified.

        """
        names = [''] * NUM_PLAYERS
        for sock in self.getUsers():
            names[sock.session['seat']] = sock.session['nickname']
        return names

    def isFull(self):
        """Check if the room is full and return a boolean.

        Lobby cannot fill up.

        """
        if self.num == LOBBY:  # Lobby never fills
            return False
        elif len(self.getUsers()) == MAX_ROOM_SIZE:
            return True
        else:
            return False

    def getAvailableSeats(self):
        """Return list of unoccupied seat numbers in the room.

        FUTURE: The seat `-1` is the non-seat/observer seat and
        is always available.

        """
        allSeats = list(range(0, MAX_ROOM_SIZE))  # + [-1]
        if self.num == LOBBY:
            return allSeats
        else:
            usedSeats = [x.session['seat'] for x in self.getUsers()]
            availableSeats = [x for x in allSeats if x not in usedSeats]
            return availableSeats

    def getSeatingChart(self):
        """Return a seating chart for the room.

        If a user does not have a seat, they are given seat = -1.

        Returns:
          list: (username, seat number) pairs for users in the room.

        """
        seatChart = []
        for sock in self.getUsers():
            name = sock.session['nickname']
            if sock.session['seat'] is None:
                seat = -1
            else:
                seat = sock.session['seat']

            seatChart.append((name, seat))

        return seatChart

    def startGame(self):
        """Perform final player checks and start game."""
        users = self.getUsers()
        sock = users[0]  # Need to get reference to the namespace

        # Prevent game from restarting if a full room empties and refills
        if self.started:
            sock[SOCKETIO_NS].emit_to_room(
                'chat',
                ['System',
                 "This game already started, so I won't start a new one."])
            return

        # Ensure all seats filled
        if len(self.getAvailableSeats()) > 0:
            # Something has gone wrong
            log.error("bad seating error in startGame()")
            sock[SOCKETIO_NS].emit_to_room('err', 'Problem starting game')
            return

        # Send out the final seat chart
        sock[SOCKETIO_NS].emit_to_room('seatChart', self.getSeatingChart())

        self.game = Game()
        initData = self.game.start_game(self.getUsernamesInRoom())

        # Send initial game data to players
        log.debug("Sending initial game data in room %s", self.num)
        sock[SOCKETIO_NS].emit_to_target_room(LOBBY, 'gameStarted', self.num)

        target_sock_map = {s.session['seat']: s[SOCKETIO_NS]
                           for s in users}

        for msg in initData:
            target_sock_map[msg['tgt']].emit('startData', msg)

        self.started = True


class GameNamespace(BaseNamespace, BroadcastMixin):
    """Namespace for all Cinch client-server communications using Socket.io."""
    def __init__(self, *args, **kwargs):
        """Initialize connection for a client to this namespace."""
        super(GameNamespace, self).__init__(*args, **kwargs)

        self.session['roomNum'] = None
        self.session['nickname'] = 'NewUser'
        self.session['seat'] = None

    def recv_connect(self):
        """Initialize connection for a client to this namespace.

        This gets called when the client first connects (as long as this
        namespace is not the Global namespace ''). A default nickname is
        assigned and the client is moved to the Lobby. Finally, the client is
        sent a list of available rooms.

        """
        self.on_room_list()

    def recv_disconnect(self):
        """Close the socket connection when client requests a disconnect."""
        self.on_exit()  # Remove user from its current room
        self.on_exit()  # Remove user from lobby

        self.disconnect(silent=True)

    def on_test(self, *args):
        """Dummy command to get the console __init__ to fire."""
        log.info('Console connected.')
        return 'ok'

    # --------------------
    # Room & chat management methods
    # --------------------

    def moveToRoom(self, room=None, roomNum=None, seat=None):
        """Leave current room and join target room.

        If both roomNum and room are provided, roomNum is ignored.

        If client is not in a room, this method will still work (leaving a
        non-existant room is legal).

        Args:
          room (Room, optional): Target Room object.
          roomNum (int or string, optional): Target room number.
          seat (int or string): Target seat.

        Raises:
          ValueError: If both roomNum and room are None.
          ValueError: If roomNum does not belong to an existing room.
          TypeError: If `room` is not an instance of Room.
          TypeError: If roomNum is not and cannot be converted to an integer.
          TypeError: If `seat` is not an integer and cannot be converted to an
            integer.
          ValueError: If the target seat is taken.

        """
        if roomNum is None and room is None:
            raise ValueError('Either `room` or `roomNum` must be provided.')
        try:
            seat = int(seat)  # seat could be a stringed integer
        except TypeError:
            raise ValueError('Arg `seat` must be an integer.')

        if room is not None:
            if not isinstance(room, Room):
                raise TypeError('Arg `room` must be of type Room.')

        else:  # roomNum is not None
            try:
                roomNum = int(roomNum)  # roomNum could be a stringed integer
            except TypeError:
                raise ValueError(
                    'Arg `roomNum` must be an integer.')

            room = self.getRoomByNumber(roomNum)
            if room is None:
                raise ValueError('That room number ({0}) does not belong to an'
                                 ' existing room'.format(roomNum))

        # Args validated now, so check for available seat
        availableSeats = room.getAvailableSeats()
        if seat in availableSeats:
            self._leaveRoom()
            self._joinRoom(room.num, seat)
        else:
            raise ValueError(
                'Target seat ({0}) is not available.'.format(seat))

    def _joinRoom(self, roomNum, seatNum=None):
        """Join room specified by room number and announce arrival.

        Arg `roomNum` is assumed to belong to a valid room, as this method
        is not called directly. Also assumes `seatNum`, if set, is available.

        Args:
          roomNum (int): Target room number.
          seatNum (int, optional): Target seat number.

        """
        self.session['roomNum'] = roomNum
        if seatNum is not None:
            self.session['seat'] = seatNum

        # Tell others in room and lobby that someone has joined and sat down
        self.emit_to_room_not_me(
            'enter', self.session['nickname'], roomNum, seatNum)
        if roomNum != LOBBY:
            self.emit_to_target_room(
                LOBBY, 'enter', self.session['nickname'], roomNum, seatNum)

    def _leaveRoom(self):
        """Leave current room and announce departure to that room.

        This method sets the client's room to None. It is up to the calling
        functions to ensure that the client is moved to a room soonest.

        """
        if self.session['roomNum'] is not None:
            self.emit_to_room_not_me(
                'exit', self.session['nickname'], self.session['roomNum'],
                self.session['seat'])

        self.session['roomNum'] = None
        self.session['seat'] = None

    def on_join(self, roomNum, seatNum):
        """Handle socket request to join target room and sit in target seat.

        Client should not allow moving directly from one room to another
        without returning to the lobby. That's done by leaving the room
        (on_exit), which automatically takes you to the lobby. Only then should
        new joins be allowed.

        Args:
          roomNum (int): Index in request[rooms] for target room.
          seatNum (int): Target seat number.

        """
        roomNum = int(roomNum)  # Arg `roomNum` is sent as unicode from browser
        room = self.getRoomByNumber(roomNum)

        if room is None:
            self.emit('err', 'That room does not exist.')
            return
        elif room.isFull():
            self.emit('err', 'That room is full.')
            return
        else:
            try:
                self.moveToRoom(roomNum=roomNum, seat=seatNum)
            except Exception as e:
                log.debug('err in on_join({1}, {2}): {0}'.format(
                    repr(e), roomNum, seatNum))
                self.emit('err', repr(e))
                return

            # If the room is now full, begin or resume the game.
            if room.isFull():
                self.emit_to_room('roomFull', roomNum)
                self.emit_to_target_room(LOBBY, 'roomFull', roomNum)

                # Without this Timer, the last person to join will receive
                # start data before room data and will not have confirmed
                # their seat/pNum.
                if room.started:
                    t = Timer(0.5, self.joinInProgress,
                              [room, seatNum, self.session['nickname']])
                else:
                    t = Timer(0.5, room.startGame)

                t.start()

            log.debug('%s joined room %s.', self.session['nickname'], roomNum)

            return dict(roomNum=roomNum, seatChart=room.getSeatingChart(),
                        mySeat=seatNum)

    def joinInProgress(self, room, seatNum, nickname):
        """Facilitate a player joining a game in progress."""
        if not room.started:
            log.error("joinInProgress fired for a game not yet started")
            return

        initData = room.game.join_game_in_progress(seatNum, nickname)
        self.emit('startData', initData)

    def on_exit(self):
        """Handle socket request to leave current room.

        This method takes an argument to maintain client compatibility.

        Leaving the room should result in the following outcomes:

        - If the client is in a game room, they should move to the Lobby. This
        may affect the visibility of the room in the Lobby. This may affect
        the continued existence of the room (if empty). Departure will be
        announced.

        - If the client is in the Lobby, they should leave the Lobby and go
        nowhere. Departure will be announced.

        - If the client is nowhere, they should remain there. This probably
        marks the end of the socket connection.

        """
        curRoomNum = self.session['roomNum']

        if curRoomNum == LOBBY or curRoomNum is None:
            # Simply leave the room
            self._leaveRoom()
            return

        curRoom = self.getRoomByNumber(curRoomNum)

        # Client is wanting to leave a game room. If room is full before user
        # leaves, tell Lobby room is no longer full.

        if curRoom.isFull():
            self.emit_to_room('roomNotFull', curRoomNum)
            self.emit_to_target_room(LOBBY, 'roomNotFull', curRoomNum)

        # The Lobby will want to know what seat is becoming available
        self.emit_to_target_room(
            LOBBY, 'exit', self.session['nickname'], curRoomNum,
            self.session['seat'])

        self._leaveRoom()

        # If room is now empty, remove the room and notify clients.
        # NOTE: this doesn't affect the actual room object, only its
        # availability to clients; this may be a memory leak. TODO investigate.
        if len(curRoom.getUsers()) == 0 and curRoomNum != LOBBY:
            self.request['rooms'].remove(curRoom)
            self.broadcast_event('roomGone', curRoom.num)

        log.debug('%s left room %s; placing in lobby.',
                  self.session['nickname'], curRoomNum)

        self.moveToRoom(roomNum=LOBBY, seat=0)

    def on_room_list(self):
        """Transmit list of available rooms and their occupants.

        Exclude the Lobby, because we don't want it in the list of rooms
        to be joined. Remove `if x.num != LOBBY` if you want the Lobby to be
        included.

        """
        roomList = [{'name': str(x), 'num': x.num, 'isFull': x.isFull(),
                     'started': x.started, 'seatChart': x.getSeatingChart()}
                    for x in self.request['rooms'] if x.num != LOBBY]

        # Not using callback as to support recv_connect
        # TODO: have all clients send a connection message when they start
        # instead of relying on recv_connect.
        self.emit('rooms', roomList)

    def on_chat(self, message):
        """Transmit chat message to room, including nickname of sender.

        If the client desires different formatting for messages that it sent,
        the client should compare its nickname to that of the chat message. The
        server sends the same data to all clients in the room.

        Args:
          message (string): Chat string from client.

        """
        if 'nickname' in self.session:
            self.emit_to_room('chat', [self.session['nickname'], message])
        else:
            self.emit('err', 'You must set a nickname first')

    def on_createRoom(self, args):
        """Create new room and announce new room's existence to clients.

        Args:
          args (dict, optional): {seat: ai_model_id, seat2: ...}

        """
        # 'rooms' is list of Room objects
        roomNum = self.request['curMaxRoomNum'] + 1
        self.request['curMaxRoomNum'] += 1
        newRoom = Room(roomNum)
        self.request['rooms'].append(newRoom)  # store new room in Server

        self.emit_to_target_room(
            LOBBY, 'newRoom', {'name': str(newRoom), 'num': roomNum,
                               'started': False, 'isFull': newRoom.isFull(),
                               'seatChart': []})

        # Summon AI players
        try:
            for seat in args.keys():
                self.emit_to_target_room(
                    LOBBY, 'summonAI', {roomNum: (int(seat), int(args[seat]))})
        except AttributeError:
            pass  # No args given

        return roomNum  # Tells user to join room

    def on_nickname(self, name):
        """Set nickname for user.

        The nickname cannot be changed while the user is in a room other than
        the lobby. This is to protect the integrity of any game logging done.

        FUTURE: Prevent multiple users from having same nickname. Will need to
        show error message to client on username entry screen.

        Args:
          name (string): Desired nickname.

        """
        if self.session['roomNum'] > LOBBY:
            self.emit('err', 'You cannot change names while in a game')
            return None
        else:
            self.session['nickname'] = name
            return name

    def localhost_only(func):
        """Decoration function for limiting access to localhost."""
        def _localhost_only(self, *args, **kwargs):
            local_hosts = set(['127.0.0.1', '::ffff:127.0.0.1', '::1'])
            if self.environ['REMOTE_ADDR'] not in local_hosts:
                log.warning('Remote address {0} tried to call local-only '
                            'method {1}'.format(self.environ['REMOTE_ADDR'],
                                                str(func)))
                return
            else:
                return func(self, *args, **kwargs)
        return _localhost_only

    @localhost_only
    def on_killRoom(self, roomNum):
        """Evict all players from a room. Only works from localhost."""
        room = self.getRoomByNumber(int(roomNum))
        if room:
            for x in room.getUsers():
                x[SOCKETIO_NS].on_exit()
            return roomNum
        else:
            return None

    # --------------------
    # AI methods
    # --------------------

    def on_aiList(self):
        """Provide client with list of available AIs and their information."""
        return self.request['aiInfo']

    def on_aiListData(self, data):
        """Receive AI identity information from AI manager."""
        self.request['aiInfo'] = data

    def on_summonAI(self, model, roomNum, seat):
        """Human client has requested an AI agent for a game room."""
        log.debug("AI model {0} summoned for Room {1} Seat {2}".format(
            model, roomNum, seat))
        self.emit_to_target_room(LOBBY, 'summonAI', {roomNum: (seat, model)})

    @localhost_only
    def on_aiOnlyGame(self, seatMap):
        """Run AI-only game (4x AI).

        Args:
          seatMap (list): A list of the AI agent models for each game seat.
            The indexes of the model numbers match the seat numbers.

        """
        seatMap = map(int, seatMap)
        seats = map(unicode, range(len(seatMap)))
        args = dict(zip(seats, seatMap))
        return self.on_createRoom(args)

    # --------------------
    # Game methods
    # --------------------

    def on_bid(self, bid):
        """Relay bid to game.

        Args:
          bid (str): Bid amount. Must be a number.

        """
        g = self.getRoomByNumber(self.session['roomNum']).game

        if 'seat' in self.session:
            pNum = self.session['seat']
        else:
            # Handle clients bidding while not seated.
            self.emit('err', 'No seat assigned; bidding not allowed.')
            log.warning('Non-seated client "%s" sent bid %s',
                        self.session['nickname'], bid)
            return

        res = g.handle_bid(pNum, int(bid))
        # False on bad bid, None for inactive player

        if res is False:
            self.emit('err', 'Bad bid: {0}'.format(bid))
        elif res is None:
            self.emit('err', "It's not your turn")
        else:
            self.emit_to_room('bid', res)

    def on_play(self, play):
        """Relay play to game.

        Args:
          play (str): Card code. Must be a number.

        """
        g = self.getRoomByNumber(self.session['roomNum']).game

        if 'seat' in self.session:
            pNum = self.session['seat']
        else:
            # Handle clients playing while not seated.
            self.emit('err', 'No seat assigned; playing not allowed.')
            log.warning('Non-seated client "%s" sent play %s',
                        self.session['nickname'], play)
            return

        res = g.handle_card_played(pNum, int(play))
        # False on bad play, None for inactive player

        if res is False:
            log.debug("on_play: illegal play attempted in seat " + str(pNum))
            self.emit('err', 'Bad play: {0}'.format(play))
        elif res is None:
            self.emit('err', "It's not your turn")
        else:
            # Multiple messages == distinct messages; happens at end of hand
            if type(res) == list:
                target_sock_map = {s.session['seat']: s[SOCKETIO_NS]
                                   for s in self.getRoomByNumber(
                                       self.session['roomNum']).getUsers()}

                for msg in res:
                    target_sock_map[msg['tgt']].emit('play', msg)

            else:
                self.emit_to_room('play', res)

    # --------------------
    # Game log methods
    # --------------------

    def on_game_log(self, gameId):
        """Return parsed game log for game with id=gameId.

        Args:
          gameId (int): ID of target game.

        Returns:
          dict: Prepared game log data.

        """
        gameData = db(db.Games.id == gameId).select().first()
        events = db(db.Events.game_id == gameId).select()
        return parseLog.prepare(gameData, events)

    def on_log_list(self):
        """Retrieve list of available game logs.

        Returns:
          list: Each list item is a dict with keys (name, id).

        """
        return db(db.Games.id > 0).select().as_list()

    # --------------------
    # Helper methods
    # --------------------

    def emit_to_room(self, event, *args, **kwargs):
        """Send message to all users in sender's room.

        Args:
          event (string): Command name for message (e.g. 'chat', 'users',
            'ack').
          args (list): Args for command specified by event.
          kwargs (dict): Keyword args passed to emit_to_target_room.

        """
        self.emit_to_target_room(
            self.session['roomNum'], event, *args, **kwargs)

    def emit_to_room_not_me(self, event, *args, **kwargs):
        """Send message to all users in sender's room except sender itself.

        This is a modified form of the same-name method in
        socketio.mixins.RoomsMixIn, adapted for our concept of a Room.

        Args:
          event (string): Command name for message (e.g. 'chat', 'users',
            'ack').
          args (list): Args for command specified by event.
          kwargs (dict): This method only supports a callback kwarg,
            identifying a method to be called when the clients respond.

        """
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        roomNum = self.session['roomNum']

        callback = kwargs.pop('callback', None)
        if callback:
            # By passing 'data', we indicate that we *want* an explicit ack
            # by the client code, not an automatic as with send().
            pkt['ack'] = 'data'
            pkt['id'] = msgid = self.socket._get_next_msgid()
            self.socket._save_ack_callback(msgid, callback)

        for sessid, socket in self.socket.server.sockets.iteritems():
            if ('roomNum' in socket.session and
               socket.session['roomNum'] == roomNum):
                if socket is self.socket:
                    continue
                else:
                    socket.send_packet(pkt)

    def emit_to_target_room(self, roomNum, event, *args, **kwargs):
        """Send message to all users in a room identified by roomNum.

        Args:
          roomNum (int): Room number of target room; can be LOBBY.
          event (string): Command name for message (e.g. 'chat', 'users',
            'ack').
          args (list): Args for command specified by event.
          kwargs (dict): This method only supports a callback kwarg,
            identifying a method to be called when the clients respond.

        """
        pkt = dict(type="event", name=event, args=args, endpoint=self.ns_name)

        callback = kwargs.pop('callback', None)
        if callback:
            # By passing 'data', we indicate that we *want* an explicit ack
            # by the client code, not an automatic as with send().
            pkt['ack'] = 'data'
            pkt['id'] = msgid = self.socket._get_next_msgid()
            self.socket._save_ack_callback(msgid, callback)

        for sessid, socket in self.socket.server.sockets.iteritems():
            if ('roomNum' in socket.session and
               socket.session['roomNum'] == roomNum):
                socket.send_packet(pkt)

    def getRoomByNumber(self, roomNum):
        """Return Room object of a given room number."""
        try:
            return [x for x in self.request['rooms'] if x.num == roomNum][0]
        except IndexError:
            log.warning(str(roomNum) + ' is not a valid room number.')
            return None


class Server(object):
    """Manages namespaces and connections while holding server-global info.

    Attributes:
      request (dict): Maintains data global to all server connections.

    """
    request = {'rooms': [], 'curMaxRoomNum': LOBBY, 'aiInfo': dict()}

    def __call__(self, environ, start_response):
        """Delegate incoming message to appropriate namespace."""
        path = environ['PATH_INFO'].strip('/')

        if path.startswith("socket.io"):
            # Client should socket connect on 'http://whatever:port/cinch'
            socketio_manage(
                environ, {SOCKETIO_NS: GameNamespace}, self.request)
        else:
            log.error("not found " + path)


def runServer():
    """Start socketio server.

    The Lobby is created during this method.

    The call to serve_forever() blocks the main thread.

    """
    log.info('Listening on port {0} for socketIO'.format(SOCKETIO_PORT))

    try:
        server = SocketIOServer(('0.0.0.0', SOCKETIO_PORT), Server(),
                                heartbeat_timeout=120,
                                resource="socket.io", policy_server=False)
        Room.server = server
        server.application.request['rooms'].append(Room(LOBBY))

        server.serve_forever()
    except KeyboardInterrupt:
        log.info('Server halted with keyboard interrupt')
    except Exception, e:
        raise e
