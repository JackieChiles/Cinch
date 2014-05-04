//Knockout.js viewmodel
function CinchViewModel() {
    var self = this;

    //Data
    self.socket = CinchApp.socket;
    self.actionQueue = []; //Don't add to this directly: call self.addAction
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

    //AI module selection
    self.ai = ko.observableArray([]);
    self.chosenAi = {}; //Contains AI modules chosen by user
    self.chosenAi[CinchApp.players.west] = ko.observable();
    self.chosenAi[CinchApp.players.north] = ko.observable();
    self.chosenAi[CinchApp.players.east] = ko.observable();

    //Functions

    //When the user chooses to enter the lobby to select a game,
    //submit nickname request and switch to lobby view
    self.enterLobby = function() {
	// Require a non-empty username
	if (self.username().length < 1) {
	    alert("A username is required.");
	    return;
	}
        self.username() && self.socket.emit('nickname', self.username(), function(msg) {
            //TODO: wait for confirmation before changing username on client
	    console.log('new nickname = ', msg);
	});
        self.activeView(CinchApp.views.lobby);
    };

    self.enterAi = function() {
        self.activeView(CinchApp.views.ai);
        self.socket.emit('aiList', '');
    };

    //When the user chooses to start a new game, request to create
    // a room and submit a nickname request
    self.startNew = function () {
        var aiSelection = {};
        var ai = {};
        var chosenAi = self.chosenAi;

        self.username() && self.socket.emit('nickname', self.username());
        
        //Loop through all AI agents chosen by the user and add them to the createRoom request
        for(ai in chosenAi) {
            if(chosenAi.hasOwnProperty(ai)) {
                chosenAi[ai]() && (aiSelection[ai] = chosenAi[ai]().id);
            }
        }

        //The format for aiSelection is { seatNumber:aiAgentId }
        self.socket.emit('createRoom', aiSelection, function(roomNum) {
	    self.socket.emit('join', roomNum, function(msg) {
                self.activeView(CinchApp.views.game);
		if (msg.roomNum != 0) {
		    console.log('seatChart: ', msg.seatChart);///TODO use only seatChart
		    self.socket.$events.seatChart(msg.seatChart);
		    self.socket.$events.users(msg.users);
		}

	    });
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

        //Adds action to queue with console message: unlockBoard() must be added within handler()
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

            for(i = 0; i < msg.length; i++) {
                self.games.push(new Game(msg[i].name, msg[i].num));
            }
        });

        addSocketHandler('aiInfo', function(msg) {
            self.ai(msg);
        });

        addSocketHandler('chat', function(msg) {
            var listElement = document.getElementById('output-list');

            //TODO: change this to be an object property instead of array element
            self.chats.push(new VisibleMessage(msg[1], msg[0]));

            //Scroll chat pane to bottom
            listElement.scrollTop = listElement.scrollHeight;
        });

        addSocketHandler('err', function(msg) {
            self.logError(msg);
        });

        addSocketHandler('newRoom', function(msg) {
            self.games.push(new Game(msg.name, msg.num));
        });

        addSocketHandler('users', function(msg) {
            var i = 0;

            self.users(msg);

            //Announce users already in-game
            if(self.activeView() === CinchApp.views.game) {
                for(i = 0; i < msg.length; i++) {
                    self.announceUser(msg[i]);
                }
            }
        });

        addSocketHandler('seatChart', function(msg) {
            var i = 0;
            var clientPNum = 0;

            //msg is an array of 2-element arrays... index 0 username, index 1 seat
            for(i = 0; i < msg.length; i++) {
                //Seat could be -1 if player not in any seat yet
                if(msg[i][1] >= 0) {
                    clientPNum = CinchApp.serverToClientPNum(msg[i][1]);
                    self.players()[clientPNum].name(msg[i][0]);
                }
            }
        });

        addSocketHandler('enter', function(msg) {
            //Add the new user to the collection and announce if in game view
            self.users.push(msg);
            self.activeView() === CinchApp.views.game && self.announceUser(msg);
        });

	addSocketHandler('exit', function(username) {
	    //Notify client that someone has left
	    self.chats.push(new VisibleMessage(['User', username, 'has departed.'].join(' '), 'System'));
	});

        addSocketHandler('roomFull', function(msg) { });

	//TODO: when client seat selection is re-enabled, move this into that
        addSocketHandler('ackSeat', function(msg) {
            self.myPlayerNum(msg);
        });

        //TODO: replace with seatChart
        addSocketHandler('userInSeat', function(msg) {
            var clientPNum = CinchApp.serverToClientPNum(msg.actor);

            self.players()[clientPNum].name(msg.name);
        });

        // Game message handlers
        addSocketHandler('startData', function(msg) {
            var app = CinchApp;

            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
            self.handleAddCards(msg);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
        });

        addSocketHandler('bid', function(msg) {
            var app = CinchApp;
            var msg = msg[0]; //TODO: Why??

            app.isNullOrUndefined(msg.dlr)      || self.dealerServer(msg.dlr);
            app.isNullOrUndefined(msg.actor)    || self.players()[CinchApp.serverToClientPNum(msg.actor)].currentBidValue(msg.bid);
            app.isNullOrUndefined(msg.mode)     || self.gameMode(msg.mode);
            app.isNullOrUndefined(msg.actvP)    || self.activePlayerNumServer(msg.actvP);
        });

        socket.on('play', function(msg) {
            var app = CinchApp;
            var msg = msg[0]; //TODO: Why??

            //First, set trump and dealer
            addSocketActionDefaultUnlock('play (trp, dlr)', msg, function(msg) {
                app.isNullOrUndefined(msg.trp) || self.trump(msg.trp);
                app.isNullOrUndefined(msg.dlr) || self.dealerServer(msg.dlr);
            });

            //Next show the card being played
            app.isNullOrUndefined(msg.actor) || addSocketAction('play (actor)', msg, function(msg) {
                self.playCard(msg.playC, CinchApp.serverToClientPNum(msg.actor));
            });
            
            //Then show the trick-end board clearing
            app.isNullOrUndefined(msg.remP) || addSocketAction('play (remP)', msg, function(msg) {
                self.handleTrickWinner(msg.remP);
            });

            //After animations execute, handle other items
            //Includes game mode, which triggers showing of hand-end screen so it must be after animations
            addSocketActionDefaultUnlock('play (trp, dlr)', msg, function(msg) {
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
            finishClearingBoard();
        }, CinchApp.boardClearDelay);
    };

    //Print a message to the chat window to announce the arrival of a user
    self.announceUser = function(username) {
        username && self.chats.push(new VisibleMessage(['User', username, 'is now in the game.'].join(' '), 'System'));
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
        self.activeView(CinchApp.views.handEnd);
    });
}
