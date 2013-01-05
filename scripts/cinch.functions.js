// AJAX/Communication

function handleResponse(result) { //Used for GET-responses; uses response queue
    if (result !== null) {
        if (result.hasOwnProperty('msgs')) {
            var updates = result.msgs;
            var curItem;
            
            while (updates.length > 0) { //Iterate over all update messages
                //Using closure to keep curUpdate change from affecting entire queue
                (function (curUpdate) {
                    CinchApp.responseQueue.push(function() {
                        handleUpdate(curUpdate);
                    });
                })(updates.shift());

                //Push trigger into queue to handle secondary (dependant) actions after each update message
                CinchApp.responseQueue.push(processSecondaryActionQueue);
            }
        }
    }
    
    processResponseQueue();  //Board lock/unlock status checked within processResponseQueue()
}

function processSecondaryActionQueue() {
    //Move secondary actions to head of primary response queue. This design ensures secondary
    //actions are handled after all primary actions in current update/response, but before any
    //actions in the next update/response.
    if (CinchApp.secondaryActionQueue.length == 0) { //Escape condition
        return;
    }
    
    //If secondary actions generate more dependent actions, process again
    CinchApp.responseQueue.unshift(function() {
        processSecondaryActionQueue();
    });
    
    //Pull items from back of secondaryActionQueue to push onto front of responseQueue
    while (CinchApp.secondaryActionQueue.length > 0) {
        CinchApp.responseQueue.unshift(CinchApp.secondaryActionQueue.pop());
    }
    
    processResponseQueue();
}

function processResponseQueue() {
    if (!CinchApp.processing) { //Prevent multiple concurrent calls to this
        CinchApp.processing = true;
        
        //Normal behavior: handleUpdate(), one message block at a time
        while (CinchApp.responseQueue.length > 0) {
            if  (CinchApp.viewModel.isBoardLocked()) {   //Stop processing, but preserve queue
                break;
            } else {
                CinchApp.responseQueue.shift()(); //Invoke the next function in the queue
            }
        }

        CinchApp.processing = false;
    }
}

function handleUpdate(update) {
    for (property in update)
        if (CinchApp.actions.hasOwnProperty(property))
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
    logDebugMessage('POST data sent: ' + JSON.stringify(data));

    $.ajax({
        url: CinchApp.serverUrl,
        type: 'POST',
        data: data,
        dataType: 'json',
        success: function (result, textStatus, jqXHR) {
            logDebugMessage('POST response from server: ' + JSON.stringify(result));
            
            handleUpdate(result);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            outputErrorMessage('Error sending data: ' + errorThrown);
        },
        complete: function (jqXHR, textStatus) {
        }
    });
}

function submitAi() {
    postData({ 'ai': 0 });
}

//TODO: make this a KO subscription?
function submitChat() {
    var messageText = $('#text-to-insert').val();

    if (messageText !== '') {
        $('#text-to-insert').val('');
        postData({'uid': CinchApp.guid, 'msg': messageText});
    }
}

function submitLobby() {
    postData({ 'lob': 0 });
}

// Other functions

function logDebugMessage(message) {
    if(CinchApp.isDebugMode) {
        CinchApp.viewModel.debugMessages.push(message);
        
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
    
    CinchApp.viewModel.chats.push(new VisibleMessage(text, name, messageType));

    //Try-catch needed in case chat pane isn't loaded yet
    //TODO: find a better solution, this isn't optimal
    try {
        //Refresh the view so JQM is aware of the change made by KO
        $('#output-list').listview('refresh');
    }
    catch(e) {
    }

    //Scroll chat pane to bottom
    listElement.scrollTop = listElement.scrollHeight;
}

function serverToClientPNum(serverNum) {
    //Adjusts serverNum to match "client is South" perspective
    return (serverNum - CinchApp.viewModel.myPlayerNum() + CinchApp.numPlayers) % CinchApp.numPlayers;
}