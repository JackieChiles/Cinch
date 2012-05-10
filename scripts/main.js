/////////////////////////////////////////////////////////////////
// Knockout custom bindings                                    //
/////////////////////////////////////////////////////////////////
ko.bindingHandlers.jqmButtonEnabled = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        //Need a try-catch to handle when this is called before JQM initialization of the control
        try {
            var enable = ko.utils.unwrapObservable(valueAccessor());
            
            if(enable) {
                if($(element).attr('data-role') === 'button') {
                    //"Link" buttons
                    $(element).removeClass('ui-disabled');
                    $(element).addClass('ui-enabled');
                }
                else {
                    //Inputs or button elements
                    $(element).button('enable');
                }
            }
            else {
                if($(element).attr('data-role') === 'button') {
                    $(element).removeClass('ui-enabled');
                    $(element).addClass('ui-disabled');
                }
                else {
                    $(element).button('disable');
                }
            }
        }
        catch (e) {
        }
    }
};

//Cbr stands for checkboxradio
ko.bindingHandlers.jqmCbrEnabled = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        //Need a try-catch to handle when this is called before JQM initialization of the control
        try {
            var enable = ko.utils.unwrapObservable(valueAccessor());
            
            if(enable) {
                $(element).checkboxradio('enable');
            }
            else {
                $(element).checkboxradio('disable');
            }
        }
        catch (e) {
        }
    }
};

//Applies a border for emphasis if condition is met
ko.bindingHandlers.activeBorder = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        var enable = ko.utils.unwrapObservable(valueAccessor());
        
        if(enable) {
            $(element).addClass('active-border');
        }
        else {
            $(element).removeClass('active-border');
        }
    }
};

//Applies the given class
ko.bindingHandlers.addClass = {
    update: function(element, valueAccessor, allBindingsAccessor) {
        $(element).addClass(ko.utils.unwrapObservable(valueAccessor()));
    }
};

/////////////////////////////////////////////////////////////////
// Main namespace                                              //
/////////////////////////////////////////////////////////////////
var CinchApp = {
    //Constants
    GAME_MODE_NEW: 0,
    NUM_PLAYERS: 4,
    NUM_TEAMS: 2,
    NUM_POSSIBLE_BIDS: 6,
    ANIM_WAIT_DELAY: 1000,
    PLAY_SURFACE_WIDTH: 290,
    PLAY_SURFACE_HEIGHT: 245,
    CARD_IMAGE_WIDTH: 72,
    CARD_IMAGE_HEIGHT: 96,
    CARD_EDGE_OFFSET: 5,
    CARD_IMAGE_DIR: 'images/',
    CARD_IMAGE_EXTENSION: '.png',
    NONE_BID_DISPLAY: '-',
    faceDownCard: function() {
        //Represents face-down cards in other players' hands, used in KO arrays for those hands
        //You may not pay 3 colorless to morph
        
        return {
            vertImagePath: this.CARD_IMAGE_DIR + 'b1fv' + this.CARD_IMAGE_EXTENSION,
            horizImagePath: this.CARD_IMAGE_DIR + 'b1fh' + this.CARD_IMAGE_EXTENSION
        };
    },
    suits: ['C', 'D', 'H', 'S'],
    suitNames: ['Clubs', 'Diamonds', 'Hearts', 'Spades'],
    ranks: ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'],
    bidEnum: {
        none: -1,
        pass: 0,
        one: 1,
        two: 2,
        three: 3,
        four: 4,
        cinch: 5
    },
    gameModeEnum: {
        play: 1,
        bid: 2
    },
    playerEnum: {
        south: 0,
        west: 1,
        north: 2,
        east: 3
    },
    bidNames: [
        'Pass',
        'One',
        'Two',
        'Three',
        'Four',
        'Cinch'
    ],
    responseModeEnum: {
        holding: 0,
        running: 1
    },
    
    //Other
    responseCount: 0, //Development
    isDebugMode: true,
    guid: 0,
    cardImagesInPlay: [], //Tracks card images for animation purposes
    trickWinner: -1, //Relative to client (self is always CinchApp.playerEnum.south)
    
    //Function queue: all GET responses go here to be processed once app is in 'running' mode
    //Any other functions can be added here as needed
    responseQueue: [],    
    processing: false, //Flag for ProcessQueue
    responseCompleteQueue: [], //Actions with dependencies go here to be ran last
    
    //If "ravenholm" is in the URL, app must be running on production server, so use that URL, otherwise use dev. URL
    serverUrl: window.location.href.indexOf('ravenholm') > -1
        ? 'http://ravenholm.dyndns.tv:2424' //Legend url
        : 'http://localhost:2424', //Development URL
    actions: {
        actvP: function (update) {
            //Must wait until after other handlers are called because some depend on previous activePlayer (like playC)
            CinchApp.responseCompleteQueue.push(function () {
                viewModel.activePlayer(serverToClientPNum(update.actvP));
            });
        },
        addC: function (update) {
            //Must wait until after other handlers are called in case cards need to be removed first (from playC handler)      
            CinchApp.responseCompleteQueue.push(function () {
                var i = 0;
                var j = 0;
                var cardsToAdd = update.addC;
                
                viewModel.encodedCards(cardsToAdd);
                
                //Populate other players' hands with face-down cards
                //Can use cardsToAdd.length to get number of cards that should be in each player's hand
                for(i = 0; i < cardsToAdd.length; i++) {
                    for(j = 1; j < CinchApp.NUM_PLAYERS; j++) { //Skip index zero (client player, face-up hand)
                        viewModel.cardsInAllHands[j].push(CinchApp.faceDownCard());
                    }
                }
            });
        },
        bid: function (update) {
            //Still previous active player, as actvP handler gets pushed into the responseCompleteQueue
            viewModel.currentBids[viewModel.activePlayer()](update.bid);
        },
        dlr: function (update) { viewModel.dealer(serverToClientPNum(update.dlr)); },
        err: function (update) { outputErrorMessage(update.err); },
        mode: function (update) {
            //The rest of the hand-end processing is done through Knockout subscriptions, etc.
            viewModel.matchPoints(update.mp || []);
            viewModel.gamePoints(update.gp || []);
            viewModel.gameMode(update.mode);
        },
        msg: function (update) { outputMessage(update.msg, viewModel.playerNames[serverToClientPNum(parseInt(update.uNum))]); },
        playC: function (update) { viewModel.playCard(update.playC); },
        pNum: function (update) { viewModel.myPlayerNum(update.pNum); },
        remP: function (update) { handleEndTrick(update.remP); },
        sco: function (update) { viewModel.gameScores(update.sco); },
        trp: function (update) { viewModel.trump(update.trp); },
        uid: function (update) {
            //Don't start long-polling until server gives valid guid
            CinchApp.guid = update.uid;
            viewModel.unlockBoard();
            startLongPoll();
        },
        win: function (update) { viewModel.winner(update.win); }
    }
};

/////////////////////////////////////////////////////////////////
// Initialization                                              //
//(this code executes when main.js loads)                      //
/////////////////////////////////////////////////////////////////
    
//Live and die are deprecated, but strangely they are the only jQuery binding functions that work here...
$('#game-page').live('pageinit', function () {
    //Kill the pageinit handler so it doesn't trigger more than once
    $('#game-page').die('pageinit');
    
    //Add a binding to the chat input to submit chats when enter is pressed
    $('#text-to-insert').keypress(function(event) {
        if ( event.which == 13 ) {
           event.preventDefault();
           $('#submit-button').click();
         }
    });
    
    $('#play-surface').attr('width', CinchApp.PLAY_SURFACE_WIDTH).attr('height', CinchApp.PLAY_SURFACE_HEIGHT);
    outputMessage("Welcome to Cinch- it's pretty rad here.", 'System');
    
    //TODO: Actually handle incompatible browsers
    if (Modernizr.canvas && Modernizr.canvastext) {
        logDebugMessage('Canvas and canvas text support detected.');
    }
    else {
        logDebugMessage('Your browser does not support canvas and canvas text.');
    }
    
    //Apply Knockout bindings
    ko.applyBindings(viewModel);
});

/////////////////////////////////////////////////////////////////
// Types                                                       //
/////////////////////////////////////////////////////////////////

//TODO: encapsulate bidNames? (parameter, local variable, etc.)

//Represents a possible bid to be made by the player
//Must be invoked with the "new" keyword
var Bid = function(parentViewModel, value, validFunction) {
    var self = this;
    
    //actualValidFunction will be the passed function if available
    //Or, if parentViewModel is a valid CinchViewModel the default isValid function will be used
    //Otherwise, we're out of options- the bid is always valid
    var actualValidFunction =
        validFunction
        || (parentViewModel instanceof CinchViewModel
        ? function() { return parentViewModel.isActivePlayer() && parentViewModel.highBid() < value; }
        : function() { return true; });
    
    this.value = value;
    this.name = CinchApp.bidNames[value] || value.toString(); //If bid name exists for value use it, otherwise use value
    this.isValid = ko.computed(actualValidFunction);
    this.submit = function() {
        postData({ 'uid': CinchApp.guid, 'bid': self.value });
    }
}

//Represents a single playable card
//Must be invoked with the "new" keyword
var Card = function(encodedCard) {
    var numRanks = CinchApp.ranks.length;
    var suitIndex = Math.floor((encodedCard - 1) / numRanks);
    
    this.encoded = encodedCard;
    this.decoded = CinchApp.ranks[this.encoded - suitIndex * numRanks - 1] + CinchApp.suits[suitIndex];   
    this.imagePath = CinchApp.CARD_IMAGE_DIR + this.decoded + CinchApp.CARD_IMAGE_EXTENSION;
    
    //Development (really just an easter egg now, I guess ??? )
    this.imagePath =
        this.imagePath.indexOf('undefined') > 0 || this.imagePath.indexOf('NaN') > 0
        ? CinchApp.CARD_IMAGE_DIR + 'undefined' + CinchApp.CARD_IMAGE_EXTENSION
        : this.imagePath;
    
    this.play = function(player) {
        var cardStartPosition = getStartPosition(player);
        var cardEndPosition = getEndPosition(player);
        
        var canvas = document.getElementById('play-surface');
        var context = canvas.getContext('2d');
        var cardImage = new Image();
        cardImage.src = this.imagePath;

        var cardGfx = new CardAnimation(cardImage, player);
        CinchApp.cardImagesInPlay[player] = cardGfx;
    }
    
    this.submit = function() {
        postData({'uid': CinchApp.guid, 'card': this.encoded});
    }
};

//Represents a single message from an entity
//Must be invoked with the "new" keyword
var VisibleMessage = function(text, name, messageType) {
    this.text = text;
    this.name = name;
    this.type = messageType || ''; //CSS class, if any, to apply special formatting
}

/////////////////////////////////////////////////////////////////
// Knockout.js viewmodel                                       //
/////////////////////////////////////////////////////////////////
function CinchViewModel() {
    var self = this; //Since this is here, recommend changing all  `this` to `self`
    var i = 0;
    var bidValidFunction;
    
    //Data
    this.playerNames = [  
        'You',
        'Left opponent',
        'Your partner',
        'Right opponent'
    ];
    this.teamNames = [
        'You',
        'Opponents'
    ];
    this.myPlayerNum = ko.observable(0); //Player num assigned by server
    this.activePlayer = ko.observable(); //Relative to client (self is always CinchApp.playerEnum.south)
    this.isActivePlayer = ko.computed(function() {
        //Client is always CinchApp.playerEnum.south
        return self.activePlayer() === CinchApp.playerEnum.south;
    });
    this.activePlayerName = ko.computed(function() {
        return self.playerNames[self.activePlayer()];
    });
    this.dealer = ko.observable(); //Relative to client (self is always CinchApp.playerEnum.south)
    this.dealerName = ko.computed(function() {
        return self.playerNames[self.dealer()];
    });
    this.trump = ko.observable();
    this.trumpName = ko.computed(function() {
        return CinchApp.suitNames[self.trump()];
    });
    this.winner = ko.observable(); //Integer, winning team. Will be 0 for players 0 & 2 and 1 for players 1 and 3.
    this.winnerName = ko.computed(function() {
        //Winning team is "You" if self.winner() matches your team, otherwise "Opponents"
        return self.myPlayerNum() % CinchApp.NUM_TEAMS == self.winner() ? self.teamNames[0] : self.teamNames[1];
    });
    this.gameMode = ko.observable();
    this.isGameStarted = ko.computed(function() {
        return self.gameMode() === CinchApp.gameModeEnum.play || self.gameMode() === CinchApp.gameModeEnum.bid;
    });
    this.gameScores = ko.observableArray([0, 0]);
    this.encodedCards = ko.observableArray([]);
    this.gamePoints = ko.observable([]);
    this.matchPoints = ko.observable([]); //Encoded strings representing taking teams of high, low, jack, and game from server
    
    //"Private" function used to process gamePoints
    var getMatchPointTeam = function(type) {
        var i = 0;
        var matchPointStrings = self.matchPoints();
        
        for(i = 0; i < matchPointStrings.length; i++) {
            if(matchPointStrings[i].indexOf(type) > -1) {
                //Return the team that got the point
                return self.teamNames[i] || '';
            }
        }
        
        //If the indicator was not found for any team, return empty string
        return '';
    };
    
    //These are just team strings used for display, not the team integer values
    //TODO: use string constants for game point types
    this.highTeam = ko.computed(function() {
        return getMatchPointTeam('h');
    });
    this.lowTeam = ko.computed(function() {
        return getMatchPointTeam('l');
    });
    this.jackTeam = ko.computed(function() {
        return getMatchPointTeam('j');
    });
    this.gameTeam = ko.computed(function() {
        return getMatchPointTeam('g');
    });
    
    this.cardsInHand = ko.computed(function() {
        //Will re-compute every time cards are added removed to hand (encodedCards)
        var j = 0;
        var handArray = [];
        
        for(j = 0; j < self.encodedCards().length; j++) {
            handArray.push(new Card(self.encodedCards()[j]));
        }
        
        return handArray;
    });
    
    //An array of items for each player's hand, indexed by CinchApp.playerEnum
    this.cardsInAllHands = [
        null, //Unused placeholder to keep indexing straight. Hand for client (face-up cards) is this.cardsInHand.
        ko.observableArray([]),
        ko.observableArray([]),
        ko.observableArray([])
    ];
    this.chats = ko.observableArray([]);
    this.debugMessages = ko.observableArray([]);
    this.currentBids = [];
    
    //Initialize currentBids
    for(i = 0; i < CinchApp.NUM_PLAYERS; i++) {
        this.currentBids.push(ko.observable(CinchApp.bidEnum.none));
    }
    
    this.currentBidsNames = ko.computed(function() {
        //Will re-compute every time a bid update is received from server (currentBids is updated)
        
        var j = 0;
        var bidNameArray = [];
        var bidValue;
        
        //Current bids have changed: re-evaluate the current bid strings
        for(j = 0; j < self.currentBids.length; j++) {
            bidValue = self.currentBids[j]();
            
            //Maybe there's a more elegant way to do this...
            bidNameArray.push(bidValue === CinchApp.bidEnum.none ? CinchApp.NONE_BID_DISPLAY : CinchApp.bidNames[bidValue]);
        }
        
        return bidNameArray;
    });
    this.highBid = ko.computed(function() {
        //Will re-compute every time a bid update is received from server (currentBids is updated)
        
        var bidValues = [];
        var j = 0;
        
        //Must get the bid values, as they're wrapped up in observables
        for(j = 0; j < self.currentBids.length; j++) {
            bidValues.push(self.currentBids[j]());
        }
        
        return Math.max.apply(null, bidValues);
    });
    this.possibleBids = [];
    
    //Create the possible bids
    for(i = 0; i < CinchApp.NUM_POSSIBLE_BIDS; i++) {
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
        
        this.possibleBids.push(new Bid(this, i, bidValidFunction));
    }
    
    //Board lock/response mode
    this.lockBoard = function () {
        this.responseMode(CinchApp.responseModeEnum.holding);
    };
    this.unlockBoard = function() {
        this.responseMode(CinchApp.responseModeEnum.running);
        processResponseQueue();
    };
    this.isBoardLocked = function() {
        return this.responseMode() == CinchApp.responseModeEnum.holding;
    };
    this.responseMode = ko.observable();
    
    //Functions
    this.playCard = function(cardNum) {
        var cardToPlay = new Card(cardNum);
        var playerOfCard = self.activePlayer(); //Still "old" activePlayer
        
        //This takes care of the animation
        cardToPlay.play(playerOfCard);
        
        if(playerOfCard === CinchApp.playerEnum.south) { //Client player
            self.encodedCards.remove(cardNum);
        }
        else {
            self.cardsInAllHands[playerOfCard].pop();
        }
    };
    this.resetBids = function() {
        var j = 0;
        
        for(j = 0; j < self.currentBids.length; j++) {
            self.currentBids[j](CinchApp.bidEnum.none);
        }
    };
    this.returnHome = function(transition) {
        //Temporary fix
        window.location = 'home.html';
        viewModel = new CinchViewModel(); //Clear the viewModel for the next game
        
        //TODO: figure out why this doesn't work. Doing changePage to #home-page doesn't seem to work either.
        //Default transition is 'slideup'
        //$.mobile.changePage( 'home.html', { transition: transition || 'slideup'} );
    };
    this.startBidding = function() {
        self.resetBids();
        openJqmDialog('#bidding-page');
    };
    
    //Subscriptions
    this.gameMode.subscribe(function(newValue) {
        //Closes or opens the bid dialog depending on the game mode
        
        if(newValue == CinchApp.gameModeEnum.bid) {
            //Delay for a second to allow the player to see all of the animations
            //TODO: change animation.js and use responseQueue to do this properly (called when animations complete)
            setTimeout(function() {
                if(self.matchPoints().length > 0) {
                    //If match points on record, hand ended, open hand end dialog. 
                    openJqmDialog('#hand-end-page');
                }
                else {
                    //Otherwise, game just started, start bidding.
                    self.startBidding();
                }
            }, CinchApp.ANIM_WAIT_DELAY);
        }
        else {
            //Navigate back to game page when in play mode
            $.mobile.changePage( '#game-page', { transition: 'slideup'} );
        }
    });
    this.winner.subscribe(function(newValue) {
        //Delay for a second to allow the player to see all of the animations
        //TODO: change animation.js and use responseQueue to do this properly (called when animations complete)
        setTimeout(function() {
            openJqmDialog('#game-end-page');
        }, CinchApp.ANIM_WAIT_DELAY);
    });
}

//TODO: migrate this to CinchApp, probably
var viewModel = new CinchViewModel();

/////////////////////////////////////////////////////////////////
// Animation                                                   //
/////////////////////////////////////////////////////////////////
function clearTable(playerNum){
    CinchApp.trickWinner = serverToClientPNum(playerNum);
    //Allow all cards in play to finish animating
    finishDrawingCards(); //Process is completed from within animation.js
}

function handleEndTrick(playerNum) {  
    viewModel.lockBoard();
    
    //Must wait until 'playC' is handled
    CinchApp.responseCompleteQueue.push(function () {
        //Wait a bit so the ending play can be seen
        setTimeout(function () {
            clearTable(playerNum);
        }, 1200);
    });
}

/////////////////////////////////////////////////////////////////
// AJAX/Communication                                          //
/////////////////////////////////////////////////////////////////
function handleResponse(result) {
    if (result !== null) {
        CinchApp.responseQueue.push(function() {
            processResponse(result);
        });
    }
    
    //If responseMode = running, then process all items in queue
    if (!viewModel.isBoardLocked()) {
        processResponseQueue();
    }
}

function processResponseQueue() {
    if (!CinchApp.processing) { //Prevent multiple concurrent calls to this
        CinchApp.processing = true;
        
        while (CinchApp.responseQueue.length > 0) {
            CinchApp.responseQueue.shift()(); //Invoke the next function in the queue
        }

        CinchApp.responseQueue.length = 0; //Clear responseQueue
        CinchApp.processing = false;
    }
}

function processResponse(result) {
    if (result.hasOwnProperty('msgs')) {
        var updates = result.msgs;

        for(var i = 0; i < updates.length; i++) {
            handleUpdate(updates[i]);
        }
    }

    //Take care of any queued items
    for(var i = 0; i < CinchApp.responseCompleteQueue.length; i++)
        CinchApp.responseCompleteQueue[i]();
        
    CinchApp.responseCompleteQueue.length = 0;
}

function handleUpdate(update) {
    for(property in update)
        if(CinchApp.actions.hasOwnProperty(property))
            CinchApp.actions[property](update);
}

function startLongPoll() {
    $.ajax({
        url: CinchApp.serverUrl,
        type: 'GET',
        data: {'uid':CinchApp.guid},
        dataType: 'json',
        success: function (result, textStatus, jqXHR) {
            //Development
            CinchApp.responseCount++;
            logDebugMessage('Long poll response ' + CinchApp.responseCount + ' received from server: ' + JSON.stringify(result));
            
            handleResponse(result);

            //No longer delaying this, but there MUST remain a time-out on the server
            //so clients don't poll rapidly when nothing is being returned
            startLongPoll();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            outputErrorMessage('Error connecting to server: ' + errorThrown);
        }
    });
}

function postData(data) {
    $.ajax({
        url: CinchApp.serverUrl,
        type: 'POST',
        data: data,
        dataType: 'json',
        success: function (result, testStatus, jqXHR) {
            setTimeout(function() {
                //Not a good way to handle this but it's just for debugging...
                //Wait a bit so the debugging area is (probably) loaded into the DOM
                logDebugMessage('POST response from server: ' + JSON.stringify(result));
            }, 500);
            
            handleUpdate(result);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            outputErrorMessage('Error sending data: ' + errorThrown);
        },
        complete: function (jqXHR, textStatus) {
        }
    });
}

//TODO: make this a KO subscription?
function submitChat() {
    var messageText = $('#text-to-insert').val();

    if (messageText !== '') {
        $('#text-to-insert').val('');
        postData({'uid': CinchApp.guid, 'msg': messageText});
    }
}

function submitJoin(gameNum, pNum) {
    postData({'join': gameNum, 'pNum': pNum});
}

function submitNew(mode) {
    postData({'game': mode});
}

/////////////////////////////////////////////////////////////////
// Other                                                       //
/////////////////////////////////////////////////////////////////
function logDebugMessage(message) {
    if(CinchApp.isDebugMode) {
        viewModel.debugMessages.push(message);
        
        //Log to the console if one is available
        if(console) {
            console.log(message);
        }
    }
}

//TODO: just extend a JQM prototype for this?
function openJqmDialog(dialogId, transition) {
    //Default transition is 'slidedown'
    $('<a />')
        .attr('href', dialogId)
        .attr('data-rel', 'dialog')
        .attr('data-transition', transition || 'slidedown')
        .appendTo('body')
        .click()
        .remove();
}

function outputErrorMessage(message) {
    outputMessage(message, 'Error', 'error-msg');
    logDebugMessage(message);
}

function outputMessage(text, name, messageType) {
    var listElement = document.getElementById('output-list');
    
    viewModel.chats.push(new VisibleMessage(text, name, messageType));

    //Refresh the view so JQM is aware of the change made by KO
    $('#output-list').listview('refresh');

    //Scroll chat pane to bottom
    listElement.scrollTop = listElement.scrollHeight;
}

function serverToClientPNum(serverNum) {
    //Adjusts serverNum to match "client is South" perspective
    return (serverNum - viewModel.myPlayerNum() + CinchApp.NUM_PLAYERS) % CinchApp.NUM_PLAYERS;
}