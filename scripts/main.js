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
var GAME_MODE_NEW = 0;
var NUM_PLAYERS = 4;
var PLAY_SURFACE_WIDTH = 290;
var PLAY_SURFACE_HEIGHT = 245;
var CARD_IMAGE_WIDTH = 72;
var CARD_IMAGE_HEIGHT = 96;
var CARD_EDGE_OFFSET = 5;
var CARD_IMAGE_DIR = 'images/';
var CARD_IMAGE_EXTENSION = '.png';
var PLAYER_DIV_PREFIX = 'player-';
var suits = ['C', 'D', 'H', 'S'];
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
var myPlayerNum = 0;
var isActivePlayer = true;
var activePlayer = 0;
    
//Development URL
var serverUrl = "http://localhost:2424"

/////////////////////////////////////////////////////////////////
// Data structures                                             //
/////////////////////////////////////////////////////////////////
var actions = {
    actvP: function(playerNum) { HandleActivePlayer(playerNum); },
    addC: function(cards) { HandleAddCards(cards); },
    err: function (errorMessage) { LogDebugMessage(errorMessage); },
    pNum: function (pNum) { myPlayerNum = pNum; },
    remC: function (card) { RemoveCard(card); },
    uid: function (uid) { guid = uid; StartLongPoll(); } //Don't start long-polling until server gives valid guid
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
    
    this.getPosition = function(player) {    
        var x = 0;
        var y = 0;
        
        if (player == playerEnum.south) { //The client
            x = PLAY_SURFACE_WIDTH / 2 - CARD_IMAGE_WIDTH / 2;
            y = PLAY_SURFACE_HEIGHT - CARD_IMAGE_HEIGHT - CARD_EDGE_OFFSET;
        }
        else if (player == playerEnum.west) {
            x = CARD_EDGE_OFFSET;
            y = PLAY_SURFACE_HEIGHT / 2 - CARD_IMAGE_HEIGHT / 2;
        }
        else if (player == playerEnum.north) {
            x = PLAY_SURFACE_WIDTH / 2 - CARD_IMAGE_WIDTH / 2;
            y = CARD_EDGE_OFFSET;
        }
        else { //Should only be playerEnum.east
            x = PLAY_SURFACE_WIDTH - CARD_IMAGE_WIDTH - CARD_EDGE_OFFSET;
            y = PLAY_SURFACE_HEIGHT / 2 - CARD_IMAGE_HEIGHT / 2;
        }
        
        return [x, y]; 
    }
    
    this.play = function(player) {
        //TODO: get permission from server to do this
        //For now just free-wheelin and playing cards without server confirmation
        
        SubmitPlay(this);
        
        var cardPosition = this.getPosition(player);
        
        var canvas = document.getElementById('play-surface');
        var context = canvas.getContext('2d');
        var cardImage = new Image();
        cardImage.src = this.imagePath;
        cardImage.onload = function () {
            context.drawImage(cardImage, cardPosition[0], cardPosition[1]);
        };
    }
};

var hand = [];
var responseCompleteQueue = [];

/////////////////////////////////////////////////////////////////
// Server response handlers                                    //
/////////////////////////////////////////////////////////////////
function HandleActivePlayer(pNum) {
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

/////////////////////////////////////////////////////////////////
// AJAX/Communication                                          //
/////////////////////////////////////////////////////////////////
function HandleResponse(result) {
    //TODO: improve chat handling
    
    var ii = 0;
    var chats = [];
    
    if (result !== null) {
        var updates = result.msgs;
        var current;
        
        lastUpdateID = result.new; 
        
        for(ii = 0; ii < updates.length; ii++) {
            current = updates[ii];
            
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
        },
        complete: function (jqXHR, textStatus) {
            //Take care of any queued items
            for(var ii = 0; ii < responseCompleteQueue.length; ii++)
                responseCompleteQueue[ii]();
                
            responseCompleteQueue.length = 0;
            
            //Delay before polling again
            setTimeout(function() {
                StartLongPoll();
            }, 3000);
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

//TODO: handle message IDs and player numbers
//This can be done once server is set up to assign them
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
    for(var ii = 0; ii < hand.length; ii++)
        hand[ii].enable();
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
        .attr('onclick', "hand[$(this).data('card')].play(0)")
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
    return (serverNum - myPlayerNum + NUM_PLAYERS) % NUM_PLAYERS;
}