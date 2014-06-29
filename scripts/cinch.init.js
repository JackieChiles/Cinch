// Initialization

CinchApp.viewModel = new CinchViewModel();

$(function () {
    var socket = CinchApp.socket;

    //Add warning when navigating away from game
    window.onbeforeunload = CinchApp.viewModel.navigateAwayMessage;

    //Apply Knockout bindings
    ko.applyBindings(CinchApp.viewModel);

    //Switch to the home view
    CinchApp.viewModel.activeView(CinchApp.views.home);

    //Set up socket listeners
    CinchApp.viewModel.setUpSocket();
        
    //Add a binding to the chat input to submit chats when enter is pressed
    $('.chat-text').keypress(function(event) {
        if ( event.which == 13 ) {
           event.preventDefault();
           $(this).nextAll('.chat-submit-button:first').click();
        }
    });

    //Add a binding to the username input to goto Lobby when enter is pressed
    $('#username-input').keypress(function(event) {
        if ( event.which == 13 ) {
           event.preventDefault();
           $('#enter-lobby-btn').click();
        }
    });

    //Set the width and height of the play surface canvas
    $('#play-surface').attr('width', CinchApp.playSurfaceWidth).attr('height', CinchApp.playSurfaceHeight);

    //Focus on username entry field
    $('#username-input').focus();
});
