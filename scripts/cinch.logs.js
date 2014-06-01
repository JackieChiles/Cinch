//JS for Cinch Game Logs page

var CinchLogApp = {
    viewModel: null,
    socket: io.connect(host_path),

    views: {
        home: 'log-list',
	game: 'log-view'
    }
};


//View model (Knockout.js)
function CinchLogViewModel() {
    var self = this;

    self.socket = CinchLogApp.socket;

    self.logList = ko.observableArray([]);
    self.gameLog = ko.observable();

    self.activeView = ko.observable();

    //Retrieve list of available game logs
    self.getLogList = function() {
	self.socket.emit('log_list', function(msg) {
	    console.log('log_list=', msg);
	    self.logList(msg);
	});
    };

    //Retrieve individual game log
    self.getGameLog = function(game_id) {
	self.socket.emit('game_log', game_id, function(msg) {
	    console.log('game_log=', msg);
	    self.gameLog(msg);
	});
    };

    self.showLogList = function() {
	self.activeView(CinchLogApp.views.home);
    };
    self.showGameLog = function(id) {
	//self.getGameLog(id);
	console.log('gonna get log for ', id);
	self.activeView(CinchLogApp.views.game);
    }

    //Subscriptions

    //copied directly from cinch.viewModel.js
    self.activeView.subscribe(function(newValue) {
        //Fades the current view out and the new view in

        //newValue is page id
        var viewClass = 'cinch-view';
        var jqElement = $('#' + newValue);
        var otherViews;
        var numOtherViews = 0;
        var duration = 5;
        var fadeInStarted = false
        var fadeIn = function() {
            jqElement.fadeIn(duration);
        };
        
        otherViews = $('.' + viewClass + ':not(#' + newValue + ')');
        numOtherViews = otherViews.size();
        
        if(numOtherViews < 1) {
            fadeIn();
        }
        else {
            otherViews.each(function(i) {
                //Fade in as a callback to the first non-hidden view, or just called if all are hidden
                if($(this).is(':not(:hidden)')) {
                    $(this).fadeOut(duration, fadeIn);
                    fadeInStarted = true;
                }
                else if(i === numOtherViews - 1 && !fadeInStarted) {
                    fadeIn();
                }
            });
        }
    });

}


//Code ran on page load
CinchLogApp.viewModel = new CinchLogViewModel();

$(function () {

    ko.applyBindings(CinchLogApp.viewModel);

    CinchLogApp.viewModel.getLogList();
    CinchLogApp.viewModel.activeView(CinchLogApp.views.home);

});
