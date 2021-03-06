//Custom Knockout binding handlers
ko.bindingHandlers.linkifiedText = {
    update: function(element, valueAccessor, allBindings) {
        var text = ko.unwrap(valueAccessor());
        var splitText = text.split(' ');
        var i = 0;
        var webUrlRegex = new RegExp("^(https?)://", "i");
        var currentSegment;

        for(i = 0; i < splitText.length; i++) {
            currentSegment = splitText[i];

            if(currentSegment.match(webUrlRegex)) {
                //Replace web URLs with links
                splitText[i] = '<a href="' + encodeURI(currentSegment) + '">' + encodeURI(currentSegment) + '</a>';
            }
            else {
                //Encode the segment with HTML entities to prevent script injection
                splitText[i] = $('<div/>').text(currentSegment).html();
            }
        }

        $(element).append(splitText.join(' '));
    }
};

//Knockout.js viewmodel
function CinchViewModel() {
    var self = this;

    //Data
    self.socket = CinchApp.socket;
    self.actionQueue = []; //Don't add to this directly: call self.addAction
    self.isWindowActive = ko.observable(true);
    self.urlParameters = ko.observable({});
    self.urlParamGame = ko.computed(function() {
        var gameNum = parseInt(self.urlParameters().game, 10);

        return isNaN(gameNum) ? null : gameNum;
    });
    self.urlParamSeat = ko.computed(function() {
        var seatNum = parseInt(self.urlParameters().seat, 10);

        return isNaN(seatNum) || seatNum >= CinchApp.numPlayers ? null : seatNum;
    });
    self.username = ko.observable('');
    self.myPlayerNum = ko.observable(0); //Player num assigned by server
    self.myTeamNum = ko.computed(function() {
        //Team number according to server
        return self.myPlayerNum() % CinchApp.numTeams;
    });
    self.curRoom = ko.observable();
    self.activeView = ko.observable();
    self.games = ko.observableArray([]);
    self.players = ko.observableArray(ko.utils.arrayMap([
            CinchApp.players.south,
            CinchApp.players.west,
            CinchApp.players.north,
            CinchApp.players.east
        ], function(pNum) {
            return new Player('-', pNum);
    }));
    self.activePlayerNumServer = ko.observable();
    self.activePlayerNum = ko.computed(function() {
        var serverNum = self.activePlayerNumServer();

        return CinchApp.isNullOrUndefined(serverNum) ? null : CinchApp.serverToClientPNum(self.activePlayerNumServer());
    });
    self.isActivePlayer = ko.computed(function() { //Active player is "me"
        return self.activePlayerNum() === CinchApp.players.south;
    });
    self.highBid = ko.computed(function() {
        return Math.max.apply(null, ko.utils.arrayMap(self.players(), function(p) {
            return p.currentBidValue();
        }));
    });
    self.possibleBids = ko.utils.arrayMap([
        CinchApp.bids.pass,
        CinchApp.bids.one,
        CinchApp.bids.two,
        CinchApp.bids.three,
        CinchApp.bids.four,
        CinchApp.bids.cinch
    ], function(b) {
        return new Bid(self, b);
    });
    self.gameScores = ko.observable([0, 0]);
    self.scoreYou = ko.computed(function() {
        return self.gameScores()[self.myTeamNum()];
    });
    self.scoreOpponent = ko.computed(function() {
        return self.gameScores()[1 - self.myTeamNum()]
    });
    self.trump = ko.observable();
    self.trumpName = ko.computed(function() {
        var trump = self.trump();

        return CinchApp.isNullOrUndefined(trump) ? null : CinchApp.suitNames[trump] || '-';
    });
    self.dealerServer = ko.observable(); //pNum for dealer from server perspective
    self.dealer = ko.computed(function() {
        var dealerServer = self.dealerServer();

        return CinchApp.isNullOrUndefined(dealerServer) ? null : CinchApp.serverToClientPNum(dealerServer);
    });
    self.dealerName = ko.computed(function() {
        var dealer = self.dealer();

        return CinchApp.isNullOrUndefined(dealer) ? null : self.players()[dealer].name() || '-';
    });
    self.trickWinnerServer = ko.observable();
    self.trickWinner = ko.computed(function() {
        var tws = self.trickWinnerServer();

        return CinchApp.isNullOrUndefined(tws) ? null : CinchApp.serverToClientPNum(tws);
    });
    self.gameMode = ko.observable();
    self.isGameStarted = ko.computed(function() {
        return self.gameMode() === CinchApp.gameModes.play || self.gameMode() === CinchApp.gameModes.bid;
    });
    self.newChat = ko.observable('');
    self.chats = ko.observableArray([]);
    self.encodedCards = ko.observableArray([]);
    self.cardsInHand = ko.computed(function() {
        return ko.utils.arrayMap(self.encodedCards(), function(cardCode) {
            return new Card(cardCode);
        });
    });

    //Retrieve animation and keyboard shortcut settings from local storage
    (function() {
        if (localStorage) {
            var enableAnimation = localStorage.getItem(CinchApp.localStorageKeys.enableAnimation);
            var enableKeyboardShortcuts = localStorage.getItem(CinchApp.localStorageKeys.enableKeyboardShortcuts);

            //Default of true
            self.enableAnimation = ko.observable(enableAnimation ? enableAnimation === 'true' : true);

            //Default of false
            self.enableKeyboardShortcuts = ko.observable(enableKeyboardShortcuts ? enableKeyboardShortcuts === 'true' : false);
        }
    })();

    self.isBoardLocked = ko.observable(false);
    self.teamNames = ko.computed(function() {
        var names = [];

        names[self.myTeamNum()] = 'You';
        names[1 - self.myTeamNum()] = 'Opponents';

        return names;
    });
    self.winner = ko.observable(); //Integer, winning team. Will be 0 for players 0 and 2 and 1 for players 1 and 3.
    self.winnerName = ko.computed(function() {
        //Return name of the winning team
        return self.winner() == 0.5 ? 'Everybody' : self.teamNames()[self.winner()];
    });
    self.isGameOver = ko.computed(function() {
        return typeof self.winner() !== 'undefined';
    });
    self.gamePoints = ko.observable([]);
    self.matchPoints = ko.observable([]); //Encoded strings representing taking teams of high, low, jack, and game from server

    //Function for determining which team got high, low, jack, or game
    self.getMatchPointTeam = function(type) {
        var i = 0;
        var matchPointStrings = self.matchPoints();
        
        for(i = 0; i < matchPointStrings.length; i++) {
            if(matchPointStrings[i].indexOf(type) > -1) {
                //Return the team that got the point
                return self.teamNames()[i] || '';
            }
        }
        
        //If the indicator was not found for any team, return empty string
        return '';
    };
    
    //These are just team strings used for display, not the team integer values
    self.highTeam = ko.computed(function() {
        return self.getMatchPointTeam(CinchApp.pointTypes.high);
    });
    self.lowTeam = ko.computed(function() {
        return self.getMatchPointTeam(CinchApp.pointTypes.low);
    });
    self.jackTeam = ko.computed(function() {
        return self.getMatchPointTeam(CinchApp.pointTypes.jack);
    });
    self.gameTeam = ko.computed(function() {
        return self.getMatchPointTeam(CinchApp.pointTypes.game);
    });

    //AI module selection
    self.ai = ko.observableArray([]);
    self.chosenAi = {}; //Contains AI modules chosen by user
    self.chosenAi[CinchApp.players.west] = ko.observable();
    self.chosenAi[CinchApp.players.north] = ko.observable();
    self.chosenAi[CinchApp.players.east] = ko.observable();

    //Seat selection
    self.selectedRoom = ko.observable();
    self.getInviteLink = function (gameNum, seatNum) {
        //Building the URL this way should work as long as we don't have any additional funky stuff like hash
        //Seat number is optional, so leave it off if not provided
        //If game number not provided, give up and just return the current URL
        return gameNum ?
            window.location.href.replace(window.location.search, "") + '?game=' + gameNum + (typeof seatNum === 'undefined' ? '' : '&seat=' + seatNum) :
            window.location.href;
    };
    self.currentRoomInviteLink = ko.computed(function() {
        return self.getInviteLink(self.curRoom());
    });

    //Functions

    //When the user chooses to enter the lobby to select a game,
    //submit nickname request and switch to lobby view
    //Or, join game immediately if query string parameters found
    self.enter = function() {
        // Require a non-empty username
        if (self.username().length < 1) {
            alert("A username is required.");
            return;
        }

        var gameNum = self.urlParamGame();
        var seatNum = self.urlParamSeat();

        self.username() && self.socket.emit('nickname', self.username(), function(msg) {
            if (msg !== null) {
                console.log('new nickname = ', msg);
            }
            // If we ever want to show the people in the lobby, will need to
            // add a callback to this action. Otherwise, this user will not appear
            // in the lobby their first time connecting.

            //Join a game if one was specified in query string, otherwise join lobby
            (gameNum && seatNum) ?
                self.socket.emit('join', gameNum, seatNum, self.joinCallback) :
                self.socket.emit('join', 0, 0);
        });

        //Load the AI list now. It might be used either in AI selection or in-game when filling empty seats.
        self.socket.emit('aiList', function(msg) {
            self.ai(msg);
        });

        //If game and seat number were specified, wait for server response to join request
        if (gameNum && !seatNum) {
            //If only gameNum was specified, go to the seat selection page for that game
            var possibleRooms = self.games().filter(function(game) {
                return game.number == gameNum;
            });

            if (possibleRooms.length > 0) {
                possibleRooms[0].select();
            }
        }
        else if (!seatNum) {
            //If gameNum and seatNum weren't specified in the query string, go to lobby
            self.activeView(CinchApp.views.lobby);
        }
    };

    //Moves user from a game room to the lobby
    self.exitToLobby = function() {
        var navigateAwayMessage = self.navigateAwayMessage();

        if(!navigateAwayMessage || (navigateAwayMessage && confirm(navigateAwayMessage))) {
            self.socket.emit('exit');
            self.socket.emit('room_list'); //Update room list in Lobby

            //Clean up from last game
            self.dealerServer(null);
            self.trump(null);
            self.matchPoints([]);
            self.gameScores([0, 0]);
            self.gameMode(null);
            self.chats([]);
            self.encodedCards([]);
            self.resetBids();
            self.winner(undefined);

            var i;
            var p;

            for (i = 1; i < 4; i++) { // Don't want to reset own name so skip 0
                p = self.players()[i];
                p.name('-');
                p.numCardsInHand(0);
            }

            //Clear board
            CinchApp.animator.boardReset();

            self.activeView(CinchApp.views.lobby);
        }
    };

    self.resetChosenAi = function() {
        self.chosenAi[CinchApp.players.west](null);
        self.chosenAi[CinchApp.players.north](null);
        self.chosenAi[CinchApp.players.east](null);
    };

    self.enterAi = function() {
        self.resetChosenAi();
        self.activeView(CinchApp.views.ai);
    };

    self.inviteAi = function(seat) {
        self.chosenAi[seat]() && self.socket.emit('summonAI', self.chosenAi[seat]().id, self.curRoom(), seat);
    };

    self.getUrlParameters = function() {
        //Adapted from http://stackoverflow.com/a/2880929/830125
        //As with almost any simple solution to query string parsing, this one has its detractors,
        //but it's good enough for our case

        var match;
        var pl = /\+/g;  // Regex for replacing addition symbol with a space
        var search = /([^&=]+)=?([^&]*)/g;
        var decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); };
        var query = window.location.search.substring(1);
        var urlParameters = {};

        while (match = search.exec(query)) {
           urlParameters[decode(match[1])] = decode(match[2]);
        }

        self.urlParameters(urlParameters);
    };

    self.joinCallback = function(msg) {
        //Message could be empty if there was an issue joining the room
        if (msg) {
            self.curRoom(msg.roomNum);
            self.activeView(CinchApp.views.game);
            self.chats([]); //Clear any chats from before game start

            if (msg.roomNum != 0) {
                self.myPlayerNum(msg.mySeat);
                self.socket.$events.seatChart(msg.seatChart);
            }
        }
        else {
            //Reset the query string in case a bad join request was made there
            self.urlParameters({});
            history.pushState(null, "Cinch Home", window.location.href.replace(window.location.search, ""));

            //Join failed, so just go to the lobby
            self.socket.emit('join', 0, 0);
            self.activeView(CinchApp.views.lobby);
        }
    };

    //When the user chooses to start a new game, request to create
    // a room and submit a nickname request
    self.startNew = function () {
        var aiSelection = {};
        var ai = {};
        var chosenAi = self.chosenAi;
        var seatNum = 0; // Room creator will always be first seat

        self.username() && self.socket.emit('nickname', self.username());
        
        //Loop through all AI agents chosen by the user and add them to the createRoom request
        for(ai in chosenAi) {
            if(chosenAi.hasOwnProperty(ai)) {
                chosenAi[ai]() && (aiSelection[ai] = chosenAi[ai]().id);
            }
        }

        //The format for aiSelection is { seatNumber:aiAgentId }
        self.socket.emit('createRoom', aiSelection, function(roomNum) {
            self.socket.emit('join', roomNum, seatNum, self.joinCallback);
        });
    };

    self.submitChat = function() {
        if(self.newChat()) {
            self.socket.emit('chat', self.newChat());
            self.newChat('');
        }
    };

    self.logError = function(msg) {
        console.log("Error: ", msg);
        self.chats.push(new VisibleMessage(msg, 'Error', CinchApp.messageTypes.error));
    };

    self.playCard = function(cardNum, playerNum) {
        var cardToPlay = new Card(cardNum);
        var cardsInPlayerHand;

        if(playerNum === CinchApp.players.south) { //Client player
            self.encodedCards.remove(cardNum);
        }
        else {
            cardsInPlayerHand = self.players()[playerNum].numCardsInHand;
            cardsInPlayerHand(cardsInPlayerHand() - 1);
        }
        
        cardToPlay.play(playerNum);
    };

    self.handEndContinue = function() {
        self.curRoom(self.isGameOver() ? self.curRoom() + " - Game Over" : self.curRoom());
        self.activeView(CinchApp.views.game);
    };

    self.resetBids = function() {
        var i = 0;
        var players = self.players();

        for(i = 0; i < players.length; i++) {
            players[i].currentBidValue(null);
        }
    };

    self.setUpSocket = function() {
        var socket = self.socket;

        //Adds action to queue with console message: unlockBoard() must be added within handler()
        //TODO Note: this isn't compatible with events that are sent multiple parameters.
        function addSocketAction(id, msg, handler) {
            self.addAction(function() {
                console.log('Running socket response for "' + id + '": ', msg);
                handler(msg);
            });
        }

        //Can be used in most cases: just unlocks at end of execution of handler
        function addSocketActionDefaultUnlock(id, msg, handler) {
            addSocketAction(id, msg, function() {
                handler(msg);
                self.unlockBoard();
            });
        }

        //This can be used for a normal socket handler
        //Some handlers must be split into multiple actions, and can be dealt with case-by-case
        function addSocketHandler(id, handler) {
            socket.on(id, function(msg) {
                addSocketActionDefaultUnlock(id, msg, handler);           
            });
        }

        //Set up socket listeners
        addSocketHandler('rooms', function(msg) {
            var i = 0;

            self.games([]); //Clear existing list

            for(i = 0; i < msg.length; i++) {
                self.games.push(new Game(msg[i]));
            }
        });

        addSocketHandler('chat', function(msg) {
            self.chats.push(new VisibleMessage(msg[1], msg[0]));

            //Scroll chat panes to bottom
            $('.output-list').each(function(index, element) {
                element.scrollTop = element.scrollHeight;
            });
        });

        addSocketHandler('err', function(msg) {
            self.logError(msg);
        });

        addSocketHandler('newRoom', function(msg) {
            self.games.push(new Game(msg));
        });

        addSocketHandler('seatChart', function(msg) {
            var i = 0, j = 0;
            var players = self.players();
            var player;
            var playerInChart = false;

            //msg is an array of 2-element arrays... index 0 username, index 1 seat
            for(i = 0; i < players.length; i++) {
                player = players[i];
                playerInChart = false;

                for(j = 0; j < msg.length; j++) {
                    if(i == CinchApp.serverToClientPNum(msg[j][1])) {
                        player.name(msg[j][0]);
                        player.empty(false);
                        playerInChart = true;

                        break;
                    }
                }

                //If player was not found in the chart, the seat is now empty
                playerInChart || player.empty(true);
            }
        });

        socket.on('enter', function(user, room, seat) {
            //Announce user if in game view
            if (self.activeView() === CinchApp.views.lobby && room == 0) {
                self.chats.push(new VisibleMessage(
                    ['User', user, 'has entered the Lobby.'].join(' '), 'System'));
            }
            else {
                self.activeView() === CinchApp.views.game && self.announceUser(user);
            }
            console.log('enter: ', user, room, seat);

            //Update the Lobby Game objects with new players
            var i;
            var tmp;
            var games = self.games();

            for (i = 0; i < games.length; i++) {
                if (games[i].number == room) {
                    tmp = games[i].seatChart();
                    tmp.push([user, seat]);
                    self.games()[i].seatChart(tmp);
                }
            }

            //Update in-game view
            if (self.activeView() === CinchApp.views.game) {
                socket.$events.seatChart(tmp);
            }
        });

        socket.on('exit', function(user, room, seat) {
            //Notify client that someone has left
            if (!(self.activeView() === CinchApp.views.lobby && room != 0)) {
                // Users in the lobby receive exit messages for all rooms in order
                // to update the seating charts for available rooms. However, we
                // should not display a "departed" message when a user leaves a
                // game room and this client is in the lobby.
                self.chats.push(new VisibleMessage(
                    ['User', user, 'has departed ',
                     (room == 0 ? 'the Lobby.' : 'Room ' + room + '.')].join(' '), 'System'));
            }
            console.log('exit: ', user, room, seat);

            //Update the Lobby Game objects
            var i, j;
            var tmp;
            var games = self.games();
            for (i = 0; i < games.length; i++) {
                if (games[i].number == room) {
                    tmp = games[i].seatChart();
                    for (j = 0; j < tmp.length; j++) {
                        if (tmp[j][0] == user && tmp[j][1] == seat) {
                            break;
                        }
                    }

                    tmp.splice(j, 1);
                    self.games()[i].seatChart(tmp);
                }
            }

            //Update in-game view
            if (self.activeView() === CinchApp.views.game) {
                socket.$events.seatChart(tmp);
            }
        });

        //Helper function for setting game full status
        function setRoomFullStatus(status, roomNum) {
            var i;
            var games = self.games();

            for (i = 0; i < games.length; i++) {
                if (games[i].number == roomNum) {
                    games[i].isFull(status);
                    self.games(games); // Update class-level observable
                    break;
                }
            }
        }

        addSocketHandler('roomFull', function(roomNum) {
            //Disallow joining of full rooms from the Lobby
            setRoomFullStatus(true, roomNum);
        });

        addSocketHandler('roomNotFull', function(roomNum) {
            //Re-allow joining of previously full room
            setRoomFullStatus(false, roomNum);
        });

        addSocketHandler('roomGone', function(roomNum) {
            //Remove room from games list
            var i;
            var games = self.games();

            for (i = 0; i < games.length; i++) {
                if (games[i].number == roomNum) {
                    games.splice(i, 1); // Remove element i from array
                    self.games(games); // Update observable array
                }
            }
        });

        addSocketHandler('gameStarted', function(roomNum) {
            ko.utils.arrayForEach(self.games(), function(item) {
                if (item.number == roomNum) {
                    item.started(true);
                }
            });
        });

        // Game message handlers
        addSocketHandler('startData', function(msg) {
            var app = CinchApp;

            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
            self.handleAddCards(msg);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);

            // 'startData' is also used for joining a game in progress
            app.isNullOrUndefined(msg.resumeData) || self.handleResumeData(msg.resumeData);
        });

        self.handleResumeData = function(data) {
            // Position cards in play
            var i;

            ko.utils.arrayForEach(self.players(), function(p) {
                p.numCardsInHand(data.handSizes[p.number]);
            });

            for (i = 0; i < data.cip.length; i++) {
                self.playCard(data.cip[i][0],
                              CinchApp.serverToClientPNum(data.cip[i][1]));
                // Compensate for playCard() reducing the displayed hand size
                self.players()[data.cip[i][1]].numCardsInHand(
                    self.players()[data.cip[i][1]].numCardsInHand() + 1);
            }
            self.trump(data.trp);
            self.gameScores(data.sco);

            // Inform player about bid status; the server does not record bid
            // history, so all the bid fields cannot be updated. Future mods to
            // how bid data is communicated may fix this.
            self.chats.push(new VisibleMessage(
                ['The most recent high bid is', data.highBid, 'made by',
                 self.players()[data.declarer].name()].join(' '), 'System'));
            self.players()[data.declarer].currentBidValue(data.highBid);
        };

        addSocketHandler('bid', function(msg) {
            var app = CinchApp;
            var msg = msg;

            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.actor)    || self.players()[CinchApp.serverToClientPNum(msg.actor)].currentBidValue(msg.bid);
            app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
        });

        socket.on('play', function(msg) {
            var app = CinchApp;
            var msg = msg;

            //First, set trump and dealer
            addSocketActionDefaultUnlock('play (trp, dlr)', msg, function(msg) {
                app.isNullOrUndefined(msg.trp) || self.trump(msg.trp);
                app.isNullOrUndefined(msg.dlr) || self.dealerServer(msg.dlr);
            });

            //Next show the card being played
            app.isNullOrUndefined(msg.actor) || addSocketAction('play (playC)', msg, function(msg) {
                self.playCard(msg.playC, CinchApp.serverToClientPNum(msg.actor));
            });
            
            //Then show the trick-end board clearing
            app.isNullOrUndefined(msg.remP) || addSocketAction('play (remP)', msg, function(msg) {
                self.handleTrickWinner(msg.remP);
            });

            //After animations execute, handle other items
            //Includes game mode, which triggers showing of hand-end screen so it must be after animations
            addSocketActionDefaultUnlock('play (sco, mp, gp, win, mode, msg, actvP)', msg, function(msg) {
                msg.sco                             && self.gameScores(msg.sco);
                msg.mp                              && self.matchPoints(msg.mp);
                msg.gp                              && self.gamePoints(msg.gp);
                app.isNullOrUndefined(msg.win)      || self.winner(msg.win);
                app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
                self.handleAddCards(msg);
                app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
            });
        });
    };

    self.handleAddCards = function(msg) {
        if(!CinchApp.isNullOrUndefined(msg.addC)) {
            var i = 0;

            self.encodedCards(msg.addC);
            for(i = 0; i < self.players().length; i++) {
                self.players()[i].numCardsInHand(msg.addC.length);
            }
        }
    };

    //Used to add actions to the queue: all must call unlockBoard() at some point.
    self.addAction = function(action) {
        //Run action if board not locked, otherwise enqueue it
        if(self.isBoardLocked()) {
            self.actionQueue.push(action);
        }
        else {
            self.lockBoard();
            action();
        }
    };

    self.lockBoard = function () {
        self.isBoardLocked(true);
    };

    self.unlockBoard = function () {
        self.isBoardLocked(false);
    };

    self.handleTrickWinner = function(pNum) {
        self.trickWinnerServer(pNum);

        //Wait a bit so the ending play can be seen
        setTimeout(function () {
            CinchApp.animator.boardClear(self.trickWinner(), self.enableAnimation());
        }, CinchApp.animator.boardClearDelay);
    };

    //Print a message to the chat window to announce the arrival of a user
    self.announceUser = function(username) {
        username && self.chats.push(new VisibleMessage(['User', username, 'is now in the game.'].join(' '), 'System'));
    };

    self.navigateAwayMessage = function() {
        var view = self.activeView();
        var views = CinchApp.views;

        return (view === views.game || view === views.handEnd) && !self.isGameOver() ? 'Leaving the page will end the current game for you.' : null;
    };

    //Subscriptions
    self.isBoardLocked.subscribe(function(newValue) {
        //If the board has been unlocked, execute the next action if available       
        if(!newValue && self.actionQueue.length > 0) {
            self.lockBoard();
            self.actionQueue.shift()();
        }
    });
    self.activeView.subscribe(function(newValue) {
        //Fades the current view out and the new view in

        //newValue is page id
        var viewClass = 'cinch-view';
        var jqElement = $('#' + newValue);
        var otherViews;
        var numOtherViews = 0;
        var duration = 5;
        var fadeInStarted = false
        var fadeIn = function() {
            jqElement.fadeIn(duration);
        };
        
        otherViews = $('.' + viewClass + ':not(#' + newValue + ')');
        numOtherViews = otherViews.size();
        
        if(numOtherViews < 1) {
            fadeIn();
        }
        else {
            otherViews.each(function(i) {
                //Fade in as a callback to the first non-hidden view, or just called if all are hidden
                if($(this).is(':not(:hidden)')) {
                    $(this).fadeOut(duration, fadeIn);
                    fadeInStarted = true;
                }
                else if(i === numOtherViews - 1 && !fadeInStarted) {
                    fadeIn();
                }
            });
        }
    });
    self.activePlayerNum.subscribe(function(newValue) {
        var i = 0;
        var players = self.players();

        for(i = 0; i < players.length; i++) {
            players[i].active(false);
        }

        players[newValue].active(true);
    });
    self.isActivePlayer.subscribe(function(newValue) {
        var notify;

        //Trigger a notification only if the window is not active and we're in the game or hand-end view
        if(newValue && ("Notification" in window) && !self.isWindowActive() && (self.activeView() === CinchApp.views.game || self.activeView() === CinchApp.views.handEnd)) {
             notify = function(permission) {
                new Notification("It's your turn to " + (self.gameMode() === CinchApp.gameModes.play ? 'play' : 'bid') + ' in Cinch.');
            };

            if(Notification.permission === 'granted') {
                notify(Notification.permission);
            }
            else if (Notification.permission !== 'denied') {
                Notification.requestPermission(notify);
            }
        }
    });
    self.gameMode.subscribe(function(newValue) {
        if(newValue == CinchApp.gameModes.bid) {
            //If match points on record, hand ended
            if(self.matchPoints().length > 0) {
                var i = 0;
            
                self.activeView(CinchApp.views.handEnd);
            
                //Clear any old bids
                self.resetBids();
                
                //Clear trump and error messages before beginning of the next hand
                self.trump(null);
                
                //Remove last hand's error messages from chat
                while(i < self.chats().length) {
                    if(self.chats()[i].type() === CinchApp.messageTypes.error) {
                        self.chats.splice(i, 1);
                    }
                    else {
                        //Only advance the counter if a message wasn't removed at the current location
                        i++;
                    }
                }
            } //Otherwise, game just started, start bidding.
        }
    });
    self.winner.subscribe(function(newValue) {
        if (typeof newValue !== 'undefined') {
            self.activeView(CinchApp.views.handEnd);
        }
    });
    self.enableAnimation.subscribe(function(newValue) {
        localStorage && localStorage.setItem(CinchApp.localStorageKeys.enableAnimation, newValue);
    });
    self.enableKeyboardShortcuts.subscribe(function(newValue) {
        localStorage && localStorage.setItem(CinchApp.localStorageKeys.enableKeyboardShortcuts, newValue);

        //Don't stay focused on the checkbox, or keyboard shortcuts won't work
        $('input').blur();
    });

    //Set up keyboard shortcuts
    $(document).keypress(function(event) {
        if (self.enableKeyboardShortcuts()) {
            var i = 0;
            var minPlayCode = 49;
            var minBidCode = 48;
            var maxPlayCode = 57;
            var maxBidCode = 53;
            var code = event.which;

            //Only handle shortcuts in game view and if active element isn't input or textarea
            if(!$(event.target).is('input, textarea') && self.activeView() === CinchApp.views.game) {
                //Look for number keys 1-9 (event codes 49-57) for play or 0-5 for bid
                if (code >= minPlayCode && code <= maxPlayCode && self.gameMode() == CinchApp.gameModes.play) {
                    var card = self.cardsInHand()[code - minPlayCode];

                    event.preventDefault();
                    card && card.submit();
                }
                else if (code >= minBidCode && code <= maxBidCode && self.gameMode() == CinchApp.gameModes.bid) {
                    var bid = self.possibleBids[code - minBidCode];

                    event.preventDefault();
                    bid && bid.isValid() && bid.submit();
                }
            }
        }
    });
}
