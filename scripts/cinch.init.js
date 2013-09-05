// Initialization

CinchApp__.viewModel = new CinchViewModel__();

$(function () {
    var socket = CinchApp__.socket;

    // Exit page cleanly
    $(window).bind("beforeunload", function() {
        socket.disconnect();
    });

    //Apply Knockout bindings
    ko.applyBindings(CinchApp__.viewModel);

    //Switch to the home view
    CinchApp__.viewModel.activeView(CinchApp__.views.home);

    //Set up socket listeners
    CinchApp__.viewModel.setUpSocket();
        
    //Add a binding to the chat input to submit chats when enter is pressed
    $('#text-to-insert').keypress(function(event) {
        if ( event.which == 13 ) {
           event.preventDefault();
           $('#submit-button').click();
        }
    });

    //Set the width and height of the play surface canvas
    $('#play-surface').attr('width', CinchApp__.playSurfaceWidth).attr('height', CinchApp__.playSurfaceHeight);
});
