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
// Constants                                                   //
/////////////////////////////////////////////////////////////////
var DOES_JACKIE_CHILES_USEFULLY_COMMENT_HIS_CODE = false;
var GAME_MODE_NEW = 0;
var NUM_PLAYERS = 4;
var TEAM_SIZE = 2;
var PLAY_SURFACE_WIDTH = 290;
var PLAY_SURFACE_HEIGHT = 245;
var CARD_IMAGE_WIDTH = 72;
var CARD_IMAGE_HEIGHT = 96;
var CARD_EDGE_OFFSET = 5;
var CARD_IMAGE_DIR = 'images/';
var CARD_IMAGE_EXTENSION = '.png';
var PLAYER_DIV_PREFIX = 'player-';
var suits = ['C', 'D', 'H', 'S'];
var suitNames = ['Clubs', 'Diamonds', 'Hearts', 'Spades'];
var ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
var playerEnum = {
    south: 0,
    west: 1,
    north: 2,
    east: 3
};
var playerNames = [  
    'You',
    'Left opponent',
    'Your partner',
    'Right opponent'
];

/////////////////////////////////////////////////////////////////
// Globals                                                     //
/////////////////////////////////////////////////////////////////

//Development
var responseCount = 0;

var lastUpdateID = 0;
var guid = 0;
var myPlayerNum = 0; //Player num assigned by server (self is always playerEnum.south)
var isActivePlayer = true;
var activePlayer = 0; //Relative to client (self is always playerEnum.south)
var gameScores = [0, 0];
var cardImagesInPlay = [];  //Tracks card images for animation purposes
var trickWinner = -1;
    
if (window.location.href.indexOf("ravenholm") > -1) {
    var serverUrl = "http://ravenholm.dyndns.tv:2424"    //Legend url
}
else {
    var serverUrl = "http://localhost:2424"    //Development URL
}

/////////////////////////////////////////////////////////////////
// Data structures                                             //
/////////////////////////////////////////////////////////////////
var actions = {
    actvP: function (playerNum) { HandleActivePlayer(playerNum); },
    addC: function (cards) { HandleAddCards(cards); },
    dlr: function(playerNum) { 
        $('#dealer-name').text(playerNames[ServerToClientPNum(playerNum)]);
        $('#dealer').pulse();
        },
    err: function (errorMessage) { LogDebugMessage(errorMessage); },
    playC: function (card) { 
        var c = new Card(card, true); 
        c.play(activePlayer); //previous activePlayer; actvP handled at end of update
        if (activePlayer == playerEnum.south) { RemoveCard(card); }
        },
    pNum: function (playerNum) { myPlayerNum = playerNum; },
    remP: function (playerNum) { HandleEndTrick(playerNum); },
    sco: function (scores) { HandleScores(scores); },
    trp: function (suit) { $('#trump-name').text(suitNames[suit]); $('#trump').pulse(); },
    //Don't start long-polling until server gives valid guid
    uid: function (uid) { guid = uid; StartLongPoll(); } 
};

var Card = function(encodedCard, enabled) {
    var numRanks = ranks.length;
    var suitIndex = Math.floor((encodedCard - 1) / numRanks);
    
    this.enabled = enabled;
    this.encoded = encodedCard;
    this.decoded = ranks[this.encoded - suitIndex * numRanks - 1] + suits[suitIndex];   
    this.imagePath = CARD_IMAGE_DIR + this.decoded + CARD_IMAGE_EXTENSION;
    
    //Development
    this.imagePath =
        this.imagePath.indexOf('undefined') > 0 || this.imagePath.indexOf('NaN') > 0
        ? CARD_IMAGE_DIR + 'undefined' + CARD_IMAGE_EXTENSION
        : this.imagePath;
        
    this.jQueryObject = CardTileFactory(this.decoded, this.enabled, this.imagePath);
    
    //Add to DOM
    this.addToHand = function() {
        $('#hand').append(this.jQueryObject).trigger("create");
    }
    
    this.remove = function() {
        $('div[data-card="' + this.decoded + '"]').remove();
    }
    
    this.enable = function() {
        this.enabled = true;
        this.jQueryObject.removeClass('ui-disabled');
    }
    
    this.disable = function() {
        this.enabled = false;
        this.jQueryObject.addClass('ui-disabled');
    }
    
    this.play = function(player) {
        var cardStartPosition = getStartPosition(player);
        var cardEndPosition = getEndPosition(player);
        
        var canvas = document.getElementById('play-surface');
        var context = canvas.getContext('2d');
        var cardImage = new Image();
        cardImage.src = this.imagePath;

        var cardGfx = new CardAnimation(cardImage, player);
        cardImagesInPlay[player] = cardGfx;
    }
    
    this.submit = function() {
        SubmitPlay(this);
    }
};

var hand = [];
var responseCompleteQueue = [];

/////////////////////////////////////////////////////////////////
// Server response handlers                                    //
/////////////////////////////////////////////////////////////////
function ClearTable(playerNum){
    trickWinner = ServerToClientPNum(playerNum);
    //Allow all cards in play to finish animating
    finishDrawingCards();
    
    //Process is completed from within animation.js
}

function HandleActivePlayer(pNum) {
    //Must wait until 'playC' is handled- needs previous active player
    
    responseCompleteQueue.push(function () {
        var playerPosition = ServerToClientPNum(pNum);
        var wasActivePlayer = isActivePlayer;        
        
        isActivePlayer = playerPosition === playerEnum.south;
        activePlayer = playerPosition;
        
        if (wasActivePlayer && !isActivePlayer) {
            //Active player was self, not anymore: disable hand
            for (card in hand) {
                if (hand.hasOwnProperty(card)) {
                    hand[card].disable();
                }
            }
        }
        else if (isActivePlayer && !wasActivePlayer) {
            //Active player is now self: enable hand
            for (card in hand) {
                if (hand.hasOwnProperty(card)) {
                    hand[card].enable();
                }
            }
        }
        
        $('#active-name').text(playerNames[playerPosition])
        $('#' + PLAYER_DIV_PREFIX + playerPosition.toString() + '>div').pulse();
        $('#active-player').pulse();
    });
}

function HandleAddCards(cards) {
    //Must wait until after other handlers are called in case cards need to be removed first
    
    responseCompleteQueue.push(function () {
        for(var ii = 0; ii < cards.length; ii++)
            AddCard(cards[ii], isActivePlayer);
    });
}

function HandleChats(messages) {
    for(var ii = 0; ii < messages.length; ii++)
        OutputMessage(messages[ii].msg, playerNames[ServerToClientPNum(parseInt(messages[ii].uNum))]);
}

function HandleEndTrick(playerNum) {
    //Must wait until 'playC' is handled
    
    //TODO: lock down active player from playing until board is cleared
    //Still a TODO after animation coding update.
    responseCompleteQueue.push(function () {
        //Wait a bit so the ending play can be seen
        setTimeout(function () {
            ClearTable(playerNum);
        }, 1200);
    });
}

function HandleScores(scores) {
    var i = 0;
    
    //TODO: throw error when these don't divide evenly? Low priority...
    //Also, this will need to be updated for games with more than two teams
    for (i = 0; i < NUM_PLAYERS / TEAM_SIZE; i++) {
        if (scores[i] !== gameScores[i]) {
            //Score for team 'i' changed
            
            if(myPlayerNum % TEAM_SIZE === i) {
                $('#score-you').text(scores[i]).pulse();
            }
            else {
                $('#score-them').text(scores[i]).pulse();
            }
        }
    }
    
    gameScores = scores;
}

/////////////////////////////////////////////////////////////////
// AJAX/Communication                                          //
/////////////////////////////////////////////////////////////////
function HandleResponse(result) {
    //TODO: improve chat handling
    
    var i = 0;
    var chats = [];
    
    if (result !== null) {
        var current;
        
        lastUpdateID = result.new;
        
        if (result.hasOwnProperty('msgs')) {
            var updates = result.msgs;
        }
        else {
                return;
        }

        for(i = 0; i < updates.length; i++) {
            current = updates[i];
            
            if(current.hasOwnProperty('msg')){
                chats.push(current);
            }
            else {
                HandleUpdate(current);
            }
            
            HandleChats(chats);
        }
    }
}

function HandleUpdate(update) {
    for(property in update)
        if(actions.hasOwnProperty(property))
            actions[property](update[property]);
}

function StartLongPoll() {
    $.ajax({
        url: serverUrl,
        type: 'GET',
        data: {'uid':guid, 'last':lastUpdateID},
        dataType: 'json',
        success: function (result, testStatus, jqXHR) {
            //Development
            responseCount++;
            LogDebugMessage('Long poll response ' + responseCount + ' received from server: ' + JSON.stringify(result));
            
            HandleResponse(result);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            LogDebugMessage('Error starting long poll: ' + errorThrown);
            StartLongPoll = 0;
        },
        complete: function (jqXHR, textStatus) {
            //Take care of any queued items
            for(var i = 0; i < responseCompleteQueue.length; i++)
                responseCompleteQueue[i]();
                
            responseCompleteQueue.length = 0;
            
            //No longer delaying this, but there MUST remain a time-out on the server
            //so clients don't poll rapidly when nothing is being returned
            StartLongPoll();
        }
    });
}

function PostData(data) {
    $.ajax({
        url: serverUrl,
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

function SubmitBid(bid) {
    PostData({'uid': guid, 'bid': bid});
}

//TODO: handle message IDs (may not be necessary- received in order)
function SubmitChat() {
    var messageText = $('#text-to-insert').val();

    if (messageText == "")
        return;
    
    $('#text-to-insert').val("");
    PostData({'uid': guid, 'msg': messageText});
}

function SubmitJoin(gameNum, pNum) {
    PostData({'join': gameNum, 'pNum': pNum});
}

function SubmitNew(mode) {
    PostData({'game': mode});
}

function SubmitPlay(card) {
    PostData({'uid': guid, 'card': card.encoded});
}

/////////////////////////////////////////////////////////////////
// Other                                                       //
/////////////////////////////////////////////////////////////////

function AddCard(cardNum, enabled) {
    var newCard = new Card(cardNum, enabled);
    
    hand[newCard.decoded] = newCard;
    hand[newCard.decoded].addToHand();
}

function RemoveCard(cardNum) {
    var cardToRemove = new Card(cardNum, true);
    
    //Exception could happen if card isn't actually in hand
    try {
        hand[cardToRemove.decoded].remove();
        delete hand[cardToRemove.decoded];
    }
    catch (e) {
        LogDebugMessage(e);
    }
}

function EnablePlaying() {
    for(var i = 0; i < hand.length; i++)
        hand[i].enable();
}

//Development
function LogDebugMessage(message) {
    var log = $('#debug-area').val();
    $('#debug-area').val(message + '\n\n' + log);
}

function OutputMessage(text, name) {
    $('#output-list').append(
        $('<li>')
        .append(
            $('<strong>', {
                text: name ? name + ': ' : ''
            })
        )
        .append(
            $('<span>', {
                text: text  
            })
            .css('font-weight', 'normal')
        )
    );
    $("#output-list").listview("refresh");
}

function CardTileFactory(card, enabled, imagePath) {
    //TODO: use more reliable method of path mapping
    //TODO: bind events instead of using "attr" ?
    
    var tile =
        $('<div>')
        .attr('data-role', 'button')
        .attr('data-card', card)
        .attr('onclick', "hand[$(this).data('card')].submit()")
        .addClass('tile-button')
        .append(
            $('<div>')
            .addClass('tile')
            .css('background-image', 'url("' + imagePath + '")')
        );
        
    if(!(enabled))
        tile = tile.addClass('ui-disabled');
        
    return tile;
}

function ServerToClientPNum(serverNum) {
    //Adjusts serverNum to match "client is South" perspective
    return (serverNum - myPlayerNum + NUM_PLAYERS) % NUM_PLAYERS;
}