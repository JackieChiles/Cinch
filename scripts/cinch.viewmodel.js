//Knockout.js viewmodel
function CinchViewModel() {
    var self = this;

    //Data
    self.socket = CinchApp.socket;
    self.username = ko.observable('');
    self.myPlayerNum = ko.observable(0); //Player num assigned by server
    self.myTeamNum = ko.computed(function() {
        //Team number according to server
        return self.myPlayerNum() % CinchApp.numTeams;
    });
    self.activeView = ko.observable();
    self.games = ko.observableArray([]);
    self.users = ko.observableArray([]);
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
    self.cardImagesInPlay = [];
    self.animationQueue = [];
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
        return self.teamNames()[self.winner()];
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

    //Functions

    //When the user chooses to enter the lobby to select a game,
    //submit nickname request and switch to lobby view
    self.enterLobby = function() {
        self.username() && self.socket.emit('nickname', self.username());
        self.activeView(CinchApp.views.lobby);
    };

    //When the user chooses to start a new game, request to create
    // a room and submit a nickname request
    self.startNew = function () {
        //TODO: enter AI view when server AI is back in action
        self.username() && self.socket.emit('nickname', self.username());
        self.socket.emit('createRoom', '');
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
        
        cardToPlay.play(playerNum);

        if(playerNum === CinchApp.players.south) { //Client player
            self.encodedCards.remove(cardNum);
        }
        else {
            cardsInPlayerHand = self.players()[playerNum].numCardsInHand;
            cardsInPlayerHand(cardsInPlayerHand() - 1);
        }
    };

    self.handEndContinue = function() {
        var views = CinchApp.views;

        self.activeView(self.isGameOver() ? views.home : views.game);
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

        //Set up socket listeners
        socket.on('rooms', function(msg) {
            var i = 0;

            console.log("'rooms' -- ", msg);

            for(i = 0; i < msg.length; i++) {
                self.games.push(new Game(msg[i], i));
            }
        });

	socket.on('aiInfo', function(msg) {
	    console.log("'aiInfo' -- ", msg);
	});

        socket.on('chat', function(msg) {
            console.log("'chat' -- ", msg);

            var listElement = document.getElementById('output-list');

            //TODO: change this to be an object property instead of array element
            self.chats.push(new VisibleMessage(msg[1], msg[0]));

            //Scroll chat pane to bottom
            listElement.scrollTop = listElement.scrollHeight;
        });

        socket.on('err', function(msg) {
            self.logError(msg);
        });

        socket.on('newRoom', function(msg) {
            console.log("'newRoom' -- ", msg);

            self.games.push(new Game(msg, self.games().length));
        });

        socket.on('ackCreate', function(msg) {
            console.log("'ackCreate' -- ", msg);

            //Join the newly created room
            socket.emit('join', msg);
        });

        socket.on('ackJoin', function(msg) {
            console.log("'ackJoin' -- ", msg);

            //Take action only if joined room was not the lobby (always ID of zero)
            //TODO: change this to be an object property instead of array element
            if(msg[0] !== 0) {
                self.activeView(CinchApp.views.game);
                self.users([]); //New room, new set of users
            }
        });

        socket.on('users', function(msg) {
            var i = 0;

            console.log("'users' -- ", msg);

            self.users(msg);

            //Announce users already in-game
            if(self.activeView() === CinchApp.views.game) {
                for(i = 0; i < msg.length; i++) {
                    self.announceUser(msg[i]);
                }
            }
        });

        socket.on('seatChart', function(msg) {
            console.log("'seatChart' -- ", msg);

	        var i = 0;
            var clientPNum = 0;

            //msg is an array of 2-element arrays... index 0 username, index 1 seat
            for(i = 0; i < msg.length; i++) {
                //Seat could be -1 if player not in any seat yet
                if(msg[i][1] > 0) {
                    clientPNum = CinchApp.serverToClientPNum(msg[i][1]);
                    self.players()[clientPNum].name(msg[i][0]);
                }
            }
        });
	

        socket.on('enter', function(msg) {
            console.log("'enter' -- ", msg);

            //Add the new user to the collection and announce if in game view
            self.users.push(msg);
            self.activeView() === CinchApp.views.game && self.announceUser(msg);
        });

        socket.on('roomFull', function(msg) {
            console.log("'roomFull' -- ", msg);
        });

        socket.on('ackSeat', function(msg) {
            console.log("'ackSeat' -- ", msg);

            self.myPlayerNum(msg);
        });

        socket.on('userInSeat', function(msg) {
            console.log("'userInSeat' -- ", msg);

            var clientPNum = CinchApp.serverToClientPNum(msg.actor);

            self.players()[clientPNum].name(msg.name);
        });

        socket.on('ackNickname', function(msg) {
            console.log("'ackNickname' -- ", msg);
            //TODO: wait for confirmation before changing username on client
        });

        // Game message handlers
        socket.on('startData', function(msg) {
            var app = CinchApp;

            console.log("'startData' -- ", msg);

            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
            self.handleAddCards(msg);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
        });

        socket.on('bid', function(msg) {
            var app = CinchApp;
            var msg = msg[0]; //TODO: Why??

            console.log("'bid' (from server) -- ", msg);

            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.actor)    || self.players()[CinchApp.serverToClientPNum(msg.actor)].currentBidValue(msg.bid);
            app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
        });

        socket.on('play', function(msg) {
            var app = CinchApp;
            var msg = msg[0]; //TODO: Why??

            console.log("'play' (from server) -- ", msg);

            app.isNullOrUndefined(msg.trp)      || self.trump(msg.trp);
            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.actor)    || self.playCard(msg.playC, CinchApp.serverToClientPNum(msg.actor));
            app.isNullOrUndefined(msg.remP)     || self.handleTrickWinner(msg.remP);
            msg.sco                             && self.gameScores(msg.sco);
            msg.mp                              && self.matchPoints(msg.mp);
            msg.gp                              && self.gamePoints(msg.gp);
            app.isNullOrUndefined(msg.win)      || self.winner(msg.win);
            app.isNullOrUndefined(msg.mode)     ||
                self.addAnimation(function() {
                    self.gameMode(msg.mode);
                });
            self.handleAddCards(msg);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
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

    self.addAnimation = function(anim) {
        //If another animation is executing, queue this one. Otherwise, lock and execute now.
        if(self.isBoardLocked()) {
            self.animationQueue.push(anim);
        }
        else {
            self.isBoardLocked(true);
            anim();
        }
    };

    self.unlockBoard = function () {
        //Execute the next animation if any
        if(self.animationQueue.length > 0) {
            self.animationQueue.shift()();
        }
        else { //If none, unlock board to allow execution of new animations
            self.isBoardLocked(false);
        }
    };

    self.handleTrickWinner = function(pNum) {
        self.trickWinnerServer(pNum);

        self.addAnimation(function() {
            //Wait a bit so the ending play can be seen
            setTimeout(function () {
                finishClearingBoard();
            }, CinchApp.boardClearDelay);
        });
    };

    //Print a message to the chat window to announce the arrival of a user
    self.announceUser = function(username) {
        username && self.chats.push(new VisibleMessage(['User', username, 'is now in the game.'].join(' '), 'System'));
    };

    //Subscriptions
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
    self.gameMode.subscribe(function(newValue) {
        if(newValue == CinchApp.gameModes.bid) {
            //If match points on record, hand ended
            if(self.matchPoints().length > 0) {
                var i = 0;
            
                //Not really an animation, but wait until animations are complete before showing hand end dialog
                //A hint of the ugly old actionQueue days, but not too bad
                self.addAnimation(function() {
                    self.activeView(CinchApp.views.handEnd);
                });
            
                //Clear any old bids
                self.resetBids();
                
                //Clear trump and error messages before beginning of the next hand
                self.trump(null);
                
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
}
