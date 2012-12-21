// Initialization

$('#home-page').live('pageinit', function () {
    //Kill the pageinit handler so it doesn't trigger more than once
    $('#home-page').die('pageinit');
    
    //Apply Knockout bindings
    ko.applyBindings(viewModel);
    
    $('#lobby-page').live('pageshow', function () {
        //Kill the pageshow handler so it doesn't trigger more than once
        $('#lobby-page').die('pageshow');
        
        submitLobby();
    });
    
    $('#ai-page').live('pageshow', function () {
        //Kill the pageshow handler so it doesn't trigger more than once
        $('#ai-page').die('pageshow');
        
        submitAi();
    });

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
        
        $('#play-surface').attr('width', CinchApp.playSurfaceWidth).attr('height', CinchApp.playSurfaceHeight);
        outputMessage("Welcome to Cinch- it's pretty rad here.", CinchApp.systemUser);
        
        //TODO: Actually handle incompatible browsers
        if (Modernizr.canvas && Modernizr.canvastext) {
            logDebugMessage('Canvas and canvas text support detected.');
        }
        else {
            logDebugMessage('Your browser does not support canvas and canvas text.');
        }
    });
});