/////////////////////////////////////////////////////////////////
// Constants                                                   //
/////////////////////////////////////////////////////////////////
var GAME_MODE_NEW = 0;
var PLAY_SURFACE_WIDTH = 290;
var PLAY_SURFACE_HEIGHT = 220;
var CARD_IMAGE_WIDTH = 72;
var CARD_IMAGE_HEIGHT = 96;
var CARD_EDGE_OFFSET = 5;
var CARD_IMAGE_DIR = 'images/';
var CARD_IMAGE_EXTENSION = '.png';
var suits = ['C', 'D', 'H', 'S'];
var ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
var playerEnum = {
    south: 0,
    west: 1,
    north: 2,
    east: 3
};

/////////////////////////////////////////////////////////////////
// Globals                                                     //
/////////////////////////////////////////////////////////////////

//Development
var responseCount = 0;

var lastChatID = 0;
var guid = 0;
var playerNum = 0;
var isActivePlayer = false;
    
//Development URL
var serverUrl = "http://localhost:2424"

/////////////////////////////////////////////////////////////////
// Data structures                                             //
/////////////////////////////////////////////////////////////////
var actions = {
    addC: function(cards) { HandleAddCards(cards); },
    err: function (errorMessage) { LogDebugMessage(errorMessage); },
    msgs: function (messages) { HandleChats(messages); },
    new: function (id) { lastChatID = id; },
    pNum: function (pNum) { playerNum = pNum; },
    remC: function (card) { RemoveCard(card); },
    uid: function (uid) { guid = uid; StartLongPoll(); } //Don't start long-polling until server gives valid guid
};

//TODO: add enable()/disable() ?
var Card = function(encodedCard, enabled) {
    this.enabled = enabled;
    this.encoded = encodedCard;
    
    var numRanks = ranks.length;
    var suitIndex = Math.floor((this.encoded - 1) / numRanks);
    
    //Translates a card integer from server to useable string
    this.decoded = ranks[this.encoded - suitIndex * numRanks - 1] + suits[suitIndex];
    
    this.imagePath = CARD_IMAGE_DIR + this.decoded + CARD_IMAGE_EXTENSION;
    
    //Development
    this.imagePath =
        this.imagePath.indexOf('undefined') > 0 || this.imagePath.indexOf('NaN') > 0
        ? CARD_IMAGE_DIR + 'undefined' + CARD_IMAGE_EXTENSION
        : this.imagePath;
    
    //Add to DOM
    this.addToHand = function() {
        $('#hand').append(CardTileFactory(this.decoded, this.enabled, this.imagePath)).trigger("create");
    }
    
    this.remove = function() {
        $('div[data-card="' + this.decoded + '"]').remove();
    }
    
    this.getPosition = function(player) {
        //TODO: actually find positions for other players
    
        var x = 0;
        var y = 0;
        
        if(player == playerEnum.south) { //The client
            x = PLAY_SURFACE_WIDTH / 2 - CARD_IMAGE_WIDTH / 2;
            y = PLAY_SURFACE_HEIGHT - CARD_IMAGE_HEIGHT - CARD_EDGE_OFFSET;
        }
        
        return [x, y]; 
    }
    
    this.play = function(player) {
        //TODO: get permission from server to do this
        //For now just free-wheelin and playing cards without server confirmation
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
function HandleAddCards(cards) {
    //Must wait until after other handlers are called in case cards need to be removed first
    
    responseCompleteQueue.push(function (card) {
        for(var ii = 0; ii < cards.length; ii++)
            AddCard(cards[ii], isActivePlayer);
    });
}

function HandleChats(messages) {
    for(var ii = 0; ii < messages.length; ii++)
        OutputMessage(messages[ii].msg);
}

/////////////////////////////////////////////////////////////////
// AJAX/Communication                                          //
/////////////////////////////////////////////////////////////////
function HandleResponse(result) {
    if (result !== null)
        for(property in result)
            if(actions.hasOwnProperty(property))
                actions[property](result[property]);
}

function StartLongPoll() {
    $.ajax({
        url: serverUrl,
        type: 'GET',
        data: {'uid':guid, 'last':lastChatID},
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
            
            HandleResponse(result);
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

//Development
function AddCard(cardNum, enabled) {
    var newCard = new Card(cardNum, enabled);
    
    hand[newCard.decoded] = newCard;
    hand[newCard.decoded].addToHand();
}

function RemoveCard(cardNum) {
    var cardToRemove = new Card(cardNum, true);
    
    try {
        hand[cardToRemove.decoded].remove();
        delete hand[cardToRemove.decoded];
    }
    catch (e) {
        LogDebugMessage(e);
    }
}

//Development
function LogDebugMessage(message) {
    var log = $('#debug-area').val();
    $('#debug-area').val(message + '\n\n' + log);
}

function OutputMessage(text) {
    $('#output-list').append(
        $('<li>', {
            text: text  
        })
    );
    $("#output-list").listview("refresh");
}

function CardTileFactory(card, enabled, imagePath) {
    //TODO: use more reliable method of path mapping
    //TODO: bind or "live" events instead of using "attr" ?
    
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