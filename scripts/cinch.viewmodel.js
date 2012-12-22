// Knockout.js viewmodel

function CinchViewModel() {
    var self = this;
    var i = 0;
    var bidValidFunction;
    
    //Data
    self.playerNames = ['You', 'Left opponent', 'Your partner', 'Right opponent'];  
    self.username = ko.observable("");
    
    //Game lobby
    self.games = ko.observableArray([]);
    
    //AI module selection
    self.ai = ko.observableArray([]);
    self.chosenAi = {}; //Contains AI modules chosen by user
    self.chosenAi[CinchApp.playerEnum.west] = ko.observable();
    self.chosenAi[CinchApp.playerEnum.north] = ko.observable();
    self.chosenAi[CinchApp.playerEnum.east] = ko.observable();
    self.uploadAi = ko.computed(function() {
        var chosenAi = self.chosenAi
        var uploadList = ['-1'];
        var currentAi;

        //Creates the list of AI modules to request
        for(ai in chosenAi) {
            if(chosenAi.hasOwnProperty(ai)) {
                currentAi = chosenAi[ai]();
                
                //Either add the AI to the list or -1 for human
                uploadList[ai] = (currentAi ? currentAi.id.toString() : '-1')
            }
        }

        //And finally return a four-part string as described in the Wiki
        return uploadList.join(',');
    });
    
    self.myPlayerNum = ko.observable(0); //Player num assigned by server
    self.myTeamNum = ko.computed(function() {
        //Team number according to server
        return self.myPlayerNum() % CinchApp.numTeams;
    });
    self.teamNames = ko.computed(function() {
        var i = 0;
        var list = [];
        
        for(i = 0; i < CinchApp.numTeams; i++) {
            //For now, any team other than 'yours' will be called 'Opponents'
            list.push(self.myTeamNum() === i ? 'You' : 'Opponents');
        }
        
        return list;
    });
    self.activePlayer = ko.observable(); //Relative to client (self is always CinchApp.playerEnum.south)
    self.isActivePlayer = ko.computed(function() {
        //Client is always CinchApp.playerEnum.south
        return self.activePlayer() === CinchApp.playerEnum.south;
    });
    self.activePlayerName = ko.computed(function() {
        return self.playerNames[self.activePlayer()];
    });
    self.dealer = ko.observable(); //Relative to client (self is always CinchApp.playerEnum.south)
    self.dealerName = ko.computed(function() {
        return self.playerNames[self.dealer()];
    });
    self.trump = ko.observable();
    self.trumpName = ko.computed(function() {
        return CinchApp.suitNames[self.trump()];
    });
    self.winner = ko.observable(); //Integer, winning team. Will be 0 for players 0 & 2 and 1 for players 1 and 3.
    self.winnerName = ko.computed(function() {
        //Return name of the winning team
        return self.teamNames()[self.winner() % CinchApp.numTeams];
    });
    self.gameMode = ko.observable();
    self.isGameStarted = ko.computed(function() {
        return self.gameMode() === CinchApp.gameModeEnum.play || self.gameMode() === CinchApp.gameModeEnum.bid;
    });
    self.gameScores = ko.observableArray([0, 0]);
    self.encodedCards = ko.observableArray([]);
    self.gamePoints = ko.observable([]);
    self.matchPoints = ko.observable([]); //Encoded strings representing taking teams of high, low, jack, and game from server
    
    //"Private" function used to process gamePoints
    var getMatchPointTeam = function(type) {
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
        return getMatchPointTeam(CinchApp.pointTypes.high);
    });
    self.lowTeam = ko.computed(function() {
        return getMatchPointTeam(CinchApp.pointTypes.low);
    });
    self.jackTeam = ko.computed(function() {
        return getMatchPointTeam(CinchApp.pointTypes.jack);
    });
    self.gameTeam = ko.computed(function() {
        return getMatchPointTeam(CinchApp.pointTypes.game);
    });
    
    self.cardsInHand = ko.computed(function() {
        //Will re-compute every time cards are added removed to hand (encodedCards)
        var j = 0;
        var handArray = [];
        
        for(j = 0; j < self.encodedCards().length; j++) {
            handArray.push(new Card(self.encodedCards()[j]));
        }
        
        return handArray;
    });
    
    //An array of items for each player's hand, indexed by CinchApp.playerEnum
    self.cardsInAllHands = [
        null, //Unused placeholder to keep indexing straight. Hand for client (face-up cards) is self.cardsInHand.
        ko.observableArray([]),
        ko.observableArray([]),
        ko.observableArray([])
    ];
    self.chats = ko.observableArray([]);
    self.debugMessages = ko.observableArray([]);
    self.currentBids = [];
    
    //Initialize currentBids
    for(i = 0; i < CinchApp.numPlayers; i++) {
        self.currentBids.push(ko.observable(CinchApp.bidEnum.none));
    }
    
    self.currentBidsNames = ko.computed(function() {
        //Will re-compute every time a bid update is received from server (currentBids is updated)
        
        var j = 0;
        var bidNameArray = [];
        var bidValue;
        
        //Current bids have changed: re-evaluate the current bid strings
        for(j = 0; j < self.currentBids.length; j++) {
            bidValue = self.currentBids[j]();
            
            //Maybe there's a more elegant way to do this...
            bidNameArray.push(bidValue === CinchApp.bidEnum.none ? CinchApp.noneBidDisplay : CinchApp.bidNames[bidValue]);
        }
        
        return bidNameArray;
    });
    self.highBid = ko.computed(function() {
        //Will re-compute every time a bid update is received from server (currentBids is updated)
        
        var bidValues = [];
        var j = 0;
        
        //Must get the bid values, as they're wrapped up in observables
        for(j = 0; j < self.currentBids.length; j++) {
            bidValues.push(self.currentBids[j]());
        }
        
        return Math.max.apply(null, bidValues);
    });
    self.highBidName = ko.computed(function() {
        return CinchApp.bidNames[self.highBid()] || CinchApp.noneBidDisplay;
    });
    self.possibleBids = [];
    
    //Create the possible bids
    for(i = 0; i < CinchApp.numPossibleBids; i++) {
        bidValidFunction =
            i === CinchApp.bidEnum.pass
            ? function() {
                //Can always pass unless you're the dealer and everyone else has passed
                return self.isActivePlayer() && !(self.dealer() === CinchApp.playerEnum.south && self.highBid() <= CinchApp.bidEnum.pass);
            }
            : i === CinchApp.bidEnum.cinch
            ? function() {
                //Can always bid Cinch if you're the dealer
                return self.isActivePlayer() && (self.highBid() < CinchApp.bidEnum.cinch || self.dealer() === CinchApp.playerEnum.south);
            }
            : null; //Passing null will cause Bid to use the default isValid function, which is OK for everything but pass or Cinch
        
        self.possibleBids.push(new Bid(self, i, bidValidFunction));
    }
    
    //Board lock/response mode
    self.lockBoard = function () {
        self.responseMode(CinchApp.responseModeEnum.holding);
        CinchApp.lockCount += 1;
    };
    self.unlockBoard = function() {
        CinchApp.lockCount -= 1;
        if (CinchApp.lockCount < 1) {  //Only unlock board if there are no remaining locks
            self.responseMode(CinchApp.responseModeEnum.running);
            processResponseQueue();
            CinchApp.lockCount = 0; //In case unlock is called absent a lock
        }
    };
    self.isBoardLocked = function() {
        return self.responseMode() == CinchApp.responseModeEnum.holding;
    };
    self.responseMode = ko.observable();
    
    //Functions
    self.endBidding = function() {
        $.mobile.changePage( '#game-page', { transition: 'slideup'} ); //Navigate back to game page
    };
    self.playCard = function(cardNum) {
        var cardToPlay = new Card(cardNum);
        var playerOfCard = self.activePlayer(); //Still "old" activePlayer
        
        //Put animation at front of secondary queue, so it always is handled
        //before end of trick procedures
        CinchApp.secondaryActionQueue.unshift(function() {
            cardToPlay.play(playerOfCard);
        });

        if(playerOfCard === CinchApp.playerEnum.south) { //Client player
            self.encodedCards.remove(cardNum);
        }
        else {
            self.cardsInAllHands[playerOfCard].pop();
        }
    };
    self.resetBids = function() {
        var j = 0;
        
        for(j = 0; j < self.currentBids.length; j++) {
            self.currentBids[j](CinchApp.bidEnum.none);
        }
    };
    self.returnHome = function(transition) {
        //Temporary fix
        window.location = 'home.html';
        viewModel = new CinchViewModel(); //Clear the viewModel for the next game
        
        //TODO: figure out why this doesn't work. Doing changePage to #home-page doesn't seem to work either.
        //Default transition is 'slideup'
        //$.mobile.changePage( 'home.html', { transition: transition || 'slideup'} );
    };
    self.startBidding = function() {
        openJqmDialog('#bidding-page');
    };
    self.startNew = function() {
        postData({
            game: CinchApp.gameModeNew,
            plrs: self.uploadAi(),
            name: self.username() || CinchApp.defaultPlayerName
        });
    };
    
    //Subscriptions
    self.gameMode.subscribe(function(newValue) {
        //Closes or opens the bid dialog depending on the game mode
        
        if(newValue == CinchApp.gameModeEnum.bid) {
            if(self.matchPoints().length > 0) {
                //If match points on record, hand ended, open hand end dialog.
                CinchApp.secondaryActionQueue.push(function() {
                    //Need to ensure this is run after all other end of trick actions, but
                    //we can't guarantee key order in the updates. So re-push this till later.
                    CinchApp.secondaryActionQueue.push(function() {
                        //Clear any old bids
                        self.resetBids();
                    
                        openJqmDialog('#hand-end-page');
                        
                        //Clear trump so it isn't displayed at the beginning of the next hand
                        self.trump(null);
                    });
                });
            }
            else {
                //Otherwise, game just started, start bidding.
                self.startBidding();
            }
        }
    });
    self.winner.subscribe(function(newValue) { //TODO: test to determine if hand-end gets processed on time
        CinchApp.secondaryActionQueue.push(function() {
            //Need to ensure this is run after all everything else, including normal
            //end of hand procedures. So re-push this till later. Twice.
            CinchApp.secondaryActionQueue.push(function() {
                CinchApp.secondaryActionQueue.push(function() {
                    openJqmDialog('#hand-end-page');
                });
            });
        });
    });
}

//TODO: migrate this to CinchApp, probably
var viewModel = new CinchViewModel();