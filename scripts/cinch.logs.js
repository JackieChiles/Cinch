//JS for Cinch Game Logs page

var CinchLogApp = CinchApp;
CinchLogApp.views = {
    home: 'log-list',
    game: 'log-view'
};


//View model
function CinchLogViewModel() {
    var self = this;

    self.socket = CinchLogApp.socket;

    self.logList = ko.observableArray([]);
    self.gameData = ko.observable();
    self.hands = ko.observableArray();
    self.selectedGame = ko.observable();
    self.activeView = ko.observable();

    self.logList.subscribe(function() {
        ko.utils.arrayForEach(self.logList(), function(item) {
            item.Timestamp = new Date(item.Timestamp);
        });
    });

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
            self.gameData(msg.gameData);
            self.hands(msg.hands);
            self.selectedGame(game_id);
	});
    };

    self.showLogList = function() {
	self.activeView(CinchLogApp.views.home);
    };

    self.showGameLog = function(id) {
	self.getGameLog(id);
	console.log('fetching game log for ', id);
	self.activeView(CinchLogApp.views.game);
    }

    self.cardMap = {};
    self.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
    self.suits = ['<span class="blackSuit">♣</span>', '<span class="redSuit">♦</span>', '<span class="redSuit">♥</span>', '<span class="blackSuit">♠</span>'];

    self.buildCardMap = function() {
        var i, suitIndex, decoded;

        for (i = 1; i <= 52; i++) {
            suitIndex = Math.floor((i - 1) / self.ranks.length);
            decoded = self.ranks[i - suitIndex * self.ranks.length - 1] + self.suits[suitIndex];
            self.cardMap[i] = decoded;
        }
    };

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
CinchApp.viewModel = new CinchLogViewModel();

$(function () {
    if ( Modernizr.websockets) {
        var socket = CinchApp.socket;

        //Apply Knockout bindings
        ko.applyBindings(CinchApp.viewModel);

        CinchLogApp.viewModel.buildCardMap();
        CinchLogApp.viewModel.getLogList();
        CinchLogApp.viewModel.activeView(CinchLogApp.views.home);
    }
    else {
        $('#browser-warning').fadeIn();
    }
});
