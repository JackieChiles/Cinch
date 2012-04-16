/////////////////////////////////////////////////////////////////
// jQuery extensions                                           //
/////////////////////////////////////////////////////////////////
$.fn.pulse = function (totalDuration, callback) {
    //Requires jquery.animate-shadow plugin, for now
    
    var self = $(this);
    var originalShadow = self.css('box-shadow');
    var duration = totalDuration ? totalDuration / 2 : 500;
    
    self.animate({ boxShadow: '0 0 30px #44f'}, duration, function () {
        self.animate({ boxShadow: originalShadow }, duration, function () {
            if(callback) { callback(); };
        });
    });
}
/////////////////////////////////////////////////////////////////
// Main namespace                                              //
/////////////////////////////////////////////////////////////////
var CinchApp = {
    //Constants
    GAME_MODE_NEW: 0,
    NUM_PLAYERS: 4,
    NUM_POSSIBLE_BIDS: 6,
    PLAY_SURFACE_WIDTH: 290,
    PLAY_SURFACE_HEIGHT: 245,
    CARD_IMAGE_WIDTH: 72,
    CARD_IMAGE_HEIGHT: 96,
    CARD_EDGE_OFFSET: 5,
    CARD_IMAGE_DIR: 'images/',
    CARD_IMAGE_EXTENSION: '.png',
    NONE_BID_DISPLAY: '-',
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
    responseQueue: [], //All GET responses go here
    processing: false, //Flag for ProcessQueue
    responseCompleteQueue: [], //Actions with dependencies go here to be ran last
    
    //If "ravenholm" is in the URL, app must be running on production server, so use that URL, otherwise use dev. URL
    serverUrl: window.location.href.indexOf("ravenholm") > -1
        ? "http://ravenholm.dyndns.tv:2424" //Legend url
        : "http://localhost:2424", //Development URL
    actions: {
        actvP: function (update) {
            //Must wait until after other handlers are called because some depend on previous activePlayer (like playC)
            CinchApp.responseCompleteQueue.push(function () {
                viewModel.activePlayer(ServerToClientPNum(update.actvP));
            });
        },
        addC: function (update) {
            //Must wait until after other handlers are called in case cards need to be removed first (from playC handler)      
            CinchApp.responseCompleteQueue.push(function () {
                viewModel.encodedCards(update.addC);
            });
        },
        bid: function (update) {
            //Still previous active player, as actvP handler gets pushed into the responseCompleteQueue
            viewModel.currentBids[viewModel.activePlayer()](update.bid);
        },
        dlr: function(update) { viewModel.dealer(ServerToClientPNum(update.dlr)); },
        err: function (update) { LogDebugMessage(update.err); },
        mode: function (update) { viewModel.gameMode(update.mode); },
        msg: function(update) { OutputMessage(update.msg, viewModel.playerNames[ServerToClientPNum(parseInt(update.uNum))]); },
        playC: function (update) { viewModel.playCard(update.playC); },
        pNum: function (update) { viewModel.myPlayerNum(update.pNum); },
        remP: function (update) { HandleEndTrick(update.remP); },
        sco: function (update) { viewModel.gameScores(update.sco); },
        trp: function (update) { viewModel.trump(update.trp); },
        uid: function (update) {
            //Don't start long-polling until server gives valid guid
            CinchApp.guid = update.uid;
            viewModel.unlockBoard();
            StartLongPoll();
        } 
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
    $("#text-to-insert").keypress(function(event) {
        if ( event.which == 13 ) {
           event.preventDefault();
           $('#submit-button').click();
         }
    });
    
    $('#play-surface').attr('width', CinchApp.PLAY_SURFACE_WIDTH).attr('height', CinchApp.PLAY_SURFACE_HEIGHT);
    OutputMessage("Welcome to Cinch- it's pretty rad here.", 'System');
    
    //TODO: Actually handle incompatible browsers
    if (Modernizr.canvas && Modernizr.canvastext) {
        LogDebugMessage('Canvas and canvas text support detected.');
    }
    else {
        LogDebugMessage('Your browser does not support canvas and canvas text.');
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
var Bid = function(self, value, validFunction) {
    //actualValidFunction will be the passed function if available
    //Or, if self is a valid CinchViewModel the default isValid function will be used
    //Otherwise, we're out of options- the bid is always valid
    var actualValidFunction =
        validFunction
        || (self instanceof CinchViewModel
        ? function() { return self.isActivePlayer() && self.highBid() < value; }
        : function() { return true; });
    
    this.value = value;
    this.name = CinchApp.bidNames[value] || value.toString(); //If bid name exists for value use it, otherwise use value
    this.isValid = ko.computed(actualValidFunction);
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
        PostData({'uid': CinchApp.guid, 'card': this.encoded});
    }
};

//Represents a single chat message from an entity
//Must be invoked with the "new" keyword
var Chat = function(text, name) {
    this.text = text;
    this.name = name;
}

/////////////////////////////////////////////////////////////////
// Knockout.js viewmodel                                       //
/////////////////////////////////////////////////////////////////
function CinchViewModel() {
    var self = this; //Since this is here, recommend changing all  `this` to `self`
    var i = 0;
    var bidValidFunction;
    var emptyBids = [];
    
    //Initialize emptyBids
    for(i = 0; i < CinchApp.NUM_PLAYERS; i++) {
        emptyBids.push(ko.observable(CinchApp.bidEnum.none));
    }
    
    //Data
    this.playerNames = [  
        'You',
        'Left opponent',
        'Your partner',
        'Right opponent'
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
    this.gameMode = ko.observable();
    this.isGameStarted = ko.computed(function() {
        return self.gameMode() === CinchApp.gameModeEnum.play || self.gameMode() === CinchApp.gameModeEnum.bid;
    });
    this.gameScores = ko.observableArray([0, 0]);
    this.encodedCards = ko.observableArray([]);
    this.cardsInHand = ko.computed(function() {
        //Will re-compute every time cards are added removed to hand (encodedCards)
        var j = 0;
        var handArray = [];
        
        for(j = 0; j < self.encodedCards().length; j++) {
            handArray.push(new Card(self.encodedCards()[j]));
        }
        
        return handArray;
    });
    this.chats = ko.observableArray([]);
    this.debugMessages = ko.observableArray([]);
    this.currentBids = emptyBids;
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
    this.selectedBid = ko.observable();
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
    
    //description
    this.lockBoard = function () {
        this.responseMode(CinchApp.responseModeEnum.holding);
    }
    this.unlockBoard = function() {
        this.responseMode(CinchApp.responseModeEnum.running);
    }
    this.isBoardLocked = function() {
        return this.responseMode() == CinchApp.responseModeEnum.holding;
    }
 
    //Response mode things
    this.responseMode = ko.observable();
    this.responseModeOnChange = ko.computed(function() {
        //When responseMode is changed to `running`, process responseQueue
        if (!self.isBoardLocked()) {
            ProcessResponseQueue();
        }
    });
    
    //Functions
    this.playCard = function(cardNum) {
        var cardToPlay = new Card(cardNum);
        
        cardToPlay.play(self.activePlayer());
        
        //This is safe to do every time: if the card isn't in hand, nothing will happen
        //If it is in hand, it will be removed
        this.encodedCards.remove(cardNum);
    }
    this.submitBid = function() {
        PostData({ 'uid': CinchApp.guid, 'bid': self.selectedBid() });
    }
    this.resetBids = function() {
        self.currentBids = emptyBids;
    };
    
    //Subscriptions
    this.gameMode.subscribe(function(newValue) {
        //Closes or opens the bid dialog depending on the game mode
        
        if(newValue == CinchApp.gameModeEnum.bid) {
            self.resetBids();
            
            //TODO: find a better way of doing this?
                //Unfortunately, JQM does not have an easier way to open dialogs programmatically, for now...
            //Open bid dialog
            $('<a />')
            .attr('href', '#bidding-page')
            .attr('data-rel', 'dialog')
            .appendTo('body')
            .click()
            .remove();
        }
        else {
            $('#bidding-page').dialog('close');
        }
    });
    
    //Custom bindings
    
    //TODO: move this out of viewModel
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
}

//TODO: migrate this to CinchApp, probably
var viewModel = new CinchViewModel();

/////////////////////////////////////////////////////////////////
// Animation                                                   //
/////////////////////////////////////////////////////////////////
function ClearTable(playerNum){

    CinchApp.trickWinner = ServerToClientPNum(playerNum);
    //Allow all cards in play to finish animating
    finishDrawingCards();

    //Process is completed from within animation.js
}

function HandleEndTrick(playerNum) {
    //Must wait until 'playC' is handled
    
    //TODO: lock down active player from playing until board is cleared
    //Still a TODO after animation coding update.
    viewModel.lockBoard();
    
    CinchApp.responseCompleteQueue.push(function () {
        //Wait a bit so the ending play can be seen
        setTimeout(function () {
            ClearTable(playerNum);
        }, 1200);
    });
}

/////////////////////////////////////////////////////////////////
// AJAX/Communication                                          //
/////////////////////////////////////////////////////////////////
function HandleResponse(result) {
    if (result !== null) {
        CinchApp.responseQueue.push(result);
    }
    
    //If responseMode = running, then process all items in queue
    if (!viewModel.isBoardLocked()) {
        ProcessResponseQueue();
    }
}

function ProcessResponseQueue() {
    if (CinchApp.processing) { //Prevent multiple concurrent calls to this
        return;
    }
    else {
        CinchApp.processing = true;
        
        while (CinchApp.responseQueue.length > 0) {
            ProcessResponse(CinchApp.responseQueue.shift());
        }

        CinchApp.responseQueue.length = 0; //Clear responseQueue
        CinchApp.processing = false;
    }
}

function ProcessResponse(result) {
    if (result.hasOwnProperty('msgs')) {
        var updates = result.msgs;

        for(var i = 0; i < updates.length; i++) {
            HandleUpdate(updates[i]);
        }
    }

    //Take care of any queued items
    for(var i = 0; i < CinchApp.responseCompleteQueue.length; i++)
        CinchApp.responseCompleteQueue[i]();
        
    CinchApp.responseCompleteQueue.length = 0;
}

function HandleUpdate(update) {
    for(property in update)
        if(CinchApp.actions.hasOwnProperty(property))
            CinchApp.actions[property](update);
}

function StartLongPoll() {
    $.ajax({
        url: CinchApp.serverUrl,
        type: 'GET',
        data: {'uid':CinchApp.guid},
        dataType: 'json',
        success: function (result, textStatus, jqXHR) {
            //Development
            CinchApp.responseCount++;
            LogDebugMessage('Long poll response ' + CinchApp.responseCount + ' received from server: ' + JSON.stringify(result));
            
            HandleResponse(result);

            //No longer delaying this, but there MUST remain a time-out on the server
            //so clients don't poll rapidly when nothing is being returned
            StartLongPoll();
        },
        error: function (jqXHR, textStatus, errorThrown) {
            LogDebugMessage('Error starting long poll: ' + errorThrown);
        }
    });
}

function PostData(data) {
    $.ajax({
        url: CinchApp.serverUrl,
        type: 'POST',
        data: data,
        dataType: 'json',
        success: function (result, testStatus, jqXHR) {
            setTimeout(function() {
                //Not a good way to handle this but it's just for debugging...
                //Wait a bit so the debugging area is (probably) loaded into the DOM
                LogDebugMessage('POST response from server: ' + JSON.stringify(result));
            }, 500);
            
            HandleUpdate(result);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            LogDebugMessage('Error sending data: ' + errorThrown);
        },
        complete: function (jqXHR, textStatus) {
        }
    });
}

//TODO: make this a KO subscription?
function SubmitChat() {
    var messageText = $('#text-to-insert').val();

    if (messageText !== "") {
        $('#text-to-insert').val("");
        PostData({'uid': CinchApp.guid, 'msg': messageText});
    }
}

function SubmitJoin(gameNum, pNum) {
    PostData({'join': gameNum, 'pNum': pNum});
}

function SubmitNew(mode) {
    PostData({'game': mode});
}

/////////////////////////////////////////////////////////////////
// Other                                                       //
/////////////////////////////////////////////////////////////////

function LogDebugMessage(message) {
    if(CinchApp.isDebugMode) {
        viewModel.debugMessages.push(message);
        
        //Log to the console if one is available
        if(console) {
            console.log(message);
        }
    }
}

function OutputMessage(text, name) {
    viewModel.chats.push(new Chat(text, name));
    $("#output-list").listview("refresh");
}

function ServerToClientPNum(serverNum) {
    //Adjusts serverNum to match "client is South" perspective
    return (serverNum - viewModel.myPlayerNum() + CinchApp.NUM_PLAYERS) % CinchApp.NUM_PLAYERS;
}