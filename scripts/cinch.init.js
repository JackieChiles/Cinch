// Initialization

CinchApp.viewModel = new CinchViewModel();

$(function () {
    var socket = CinchApp.socket;

    // Exit page cleanly
    $(window).bind("beforeunload", function() {
        socket.disconnect();
    });

    //Apply Knockout bindings
    ko.applyBindings(CinchApp.viewModel);

    //Switch to the home view
    CinchApp.viewModel.activeView(CinchApp.views.home);

    //Set up socket listeners
    CinchApp.viewModel.setUpSocket();
        
    //Add a binding to the chat input to submit chats when enter is pressed
    $('#text-to-insert').keypress(function(event) {
        if ( event.which == 13 ) {
           event.preventDefault();
           $('#submit-button').click();
        }
    });

    //Set the width and height of the play surface canvas
    $('#play-surface').attr('width', CinchApp.playSurfaceWidth).attr('height', CinchApp.playSurfaceHeight);
});
