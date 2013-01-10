// Initialization

CinchApp.viewModel = new CinchViewModel();

$(function () {
    //Apply Knockout bindings
    ko.applyBindings(CinchApp.viewModel);
        
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