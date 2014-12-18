// Initialization

CinchApp.viewModel = new CinchViewModel();

$(function () {
    if(Modernizr.websockets) {
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

        //Focus on username entry field
        $('#username-input').focus();

        //Set up detection for the window/tab being active
        $(window).blur(function() {
            CinchApp.viewModel.isWindowActive(false);
        });

        $(window).focus(function() {
            CinchApp.viewModel.isWindowActive(true);
        });

        //Parse the URL query string
        CinchApp.viewModel.getUrlParameters();

        //Highlight the text of invite links when focused
        $('.invite-link').mouseup(function() {
            //Eliminates a de-select in some Webkit browsers
            return false;
        });

        $('.invite-link').focus(function() {
            $(this).select();
        });
    }
    else {
        $('#browser-warning').fadeIn();
    }
});
