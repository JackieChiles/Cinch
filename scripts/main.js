/////////////////////////////////////////////////////////////////
// Constants                                                   //
/////////////////////////////////////////////////////////////////
var GAME_MODE_NEW = 0;

/////////////////////////////////////////////////////////////////
// Globals                                                     //
/////////////////////////////////////////////////////////////////
//Development
var pos = 25;
var responseCount = 0;

var isPolling = false;
var lastChatID = 0;
var guid = 3;
var playerNum = 0;
    
//Development URL
var serverUrl = "http://localhost:2424"

/////////////////////////////////////////////////////////////////
// Data structures                                             //
/////////////////////////////////////////////////////////////////
var actions = {
    err: function (errorMessage) { LogDebugMessage(errorMessage); },
    msgs: function (messages) { HandleChats(messages); },
    new: function (id) { lastChatID = id; },
    pNum: function (pNum) { playerNum = pNum; },
    uid: function (uid) { guid = uid; }
};

/////////////////////////////////////////////////////////////////
// Server response handlers                                    //
/////////////////////////////////////////////////////////////////
function HandleChats(messages) {
    for(var ii = 0; ii < messages.length; ii++)
        OutputMessage(messages[ii].msg);
}

/////////////////////////////////////////////////////////////////
// AJAX/Communication                                          //
/////////////////////////////////////////////////////////////////
function StartLongPoll() {
    $.ajax({
        url: serverUrl,
        type: 'GET',
        data: {'uid':guid, 'last':lastChatID},
        dataType: 'json',
        success: function (result, testStatus, jqXHR) {
            isPolling = true;
            
            //Development
            responseCount++;
            LogDebugMessage('Long poll response ' + responseCount + ' received from server: ' + JSON.stringify(result));
            
            if (result !== null)
                for(property in result)
                    if(actions.hasOwnProperty(property))
                        actions[property](result[property]);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            LogDebugMessage('Error starting long poll: ' + errorThrown);
        },
        complete: function (jqXHR, textStatus) {
            //Delay before polling again
            setTimeout(function() {
                StartLongPoll();
            }, 3000);
        }
    });
}

function PostData(data) {
    //Don't POST anything until connection with the server is established
    //TODO: Make this not terrible: don't use SetTimeout, make queue of calls to
    //be made once polling starts or something
    if(isPolling) {
        $.ajax({
            url: serverUrl,
            data: data,
            type: 'POST',
            success: function (result, testStatus, jqXHR) {
                LogDebugMessage('POST response from server: ' + result);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                LogDebugMessage('Error sending chat: ' + errorThrown);
            },
            complete: function (jqXHR, textStatus) {
            }
        });
    }
    else {
        setTimeout( function() {
            PostData(data);
        }, 1000);
    }
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

function SubmitJoin(gameNum) {
    PostData({'join': gameNum});
}

function SubmitNew(mode) {
    PostData({'game': mode});
}
/////////////////////////////////////////////////////////////////
// Other                                                       //
/////////////////////////////////////////////////////////////////

function CanvasCard(cardName) {
    var canvas = document.getElementById('play-surface');
    var context = canvas.getContext('2d');
    var cardImage = new Image();
    cardImage.src = 'images/' + cardName + '.png';
    cardImage.onload = function () {
        context.drawImage(cardImage, pos, pos);
    };
    
    pos += 15;
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