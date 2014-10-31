// Classes (invoked with new keyword only)

//Represents a single joinable game, as listed in the lobby
function Game(gameMsg) {
    var self = this;

    self.name = gameMsg.name;
    self.number = gameMsg.num;
    self.isFull = ko.observable(gameMsg.isFull);
    self.seatChart = ko.observableArray(gameMsg.seatChart);
    self.seats = ko.computed(function() {
        var seats = {};
        var players = CinchApp.players;

        [players.north, players.south, players.east, players.west].forEach(function(pNum) {
            var seatChartName = null;

            //Extract the name from the seat chart if someone is there
            self.seatChart().forEach(function(chartItem) {
                chartItem[1] === pNum && (seatChartName = chartItem[0]);
            });

            //Create an seat object in place (could move to a class if needed elsewhere)
            seats[pNum] = {
                available: seatChartName === null,
                displayText: seatChartName === null ? '<Available>' : seatChartName,
                join: function() {
                    self.join(pNum);
                }
            };
        });

        return seats;
    });

    // Gets unordered list of users in the room
    self.playerNames = ko.computed(function () {
        var users = [];
        var i;
        var seatChart = self.seatChart();

        for (i = 0; i < seatChart.length; i++) {
            users.push(seatChart[i][0]);
        }

        return users; 
    });

    self.select = function() {
        CinchApp.viewModel.selectedRoom(self);
        CinchApp.viewModel.activeView(CinchApp.views.seatSelect);
    };

    // Only called when joining existing game, not ICW new
    self.join = function(seatNum) {
        CinchApp.socket.emit('join', self.number, seatNum, CinchApp.viewModel.joinCallback);
    };
}

function Player(name, number) {
    var self = this;

    self.name = ko.observable(name);
    self.number = number;
    self.active = ko.observable(false);
    self.empty = ko.observable(true);
    self.numCardsInHand = ko.observable(0);
    self.currentBidValue = ko.observable(null);
    self.currentBidName = ko.computed(function() {
        var bid = self.currentBidValue();

        return CinchApp.isNullOrUndefined(bid) ? '-' : CinchApp.bidNames[bid];
    });    
}

//Represents a single message from an entity
function VisibleMessage(text, name, messageType) {
    var self = this;

    self.text = text;
    self.name = name;
    self.type = ko.observable(messageType || CinchApp.messageTypes.normal);
    self.cssClass = ko.computed(function() {
        return self.type() === CinchApp.messageTypes.error ? 'error-msg' : '';
    });
}

//Represents a single playable card
function Card(encodedCard) {
    var numRanks = CinchApp.ranks.length;
    var suitIndex = Math.floor((encodedCard - 1) / numRanks);
    var self = this;
    
    self.encoded = encodedCard;
    self.decoded = CinchApp.ranks[self.encoded - suitIndex * numRanks - 1] + CinchApp.suits[suitIndex];   
    self.imagePath = CinchApp.cardImageDir + self.decoded + CinchApp.cardImageExtension;
    
    self.play = function(player) {
        var cardImage = new Image();

        cardImage.onload = function() {
            CinchApp.viewModel.cardImagesInPlay[player] = new CardAnimation(cardImage, player);
        };

    cardImage.onerror = function() {
        CinchApp.viewModel.chats.push(new VisibleMessage('Player '+player+' played '+self.decoded+' but the image failed to load.', 'Error', CinchApp.messageTypes.error));
        cardImage.src = null;
        CinchApp.viewModel.cardImagesInPlay[player] = new CardAnimation(cardImage, player); //Go ahead and animate a nothing card to let the game advance
    };

        cardImage.src = self.imagePath;
    };
    
    self.submit = function() {
        CinchApp.socket.emit('play', self.encoded);
    };
}

//Represents a possible bid to be made by the player
function Bid(parentViewModel, value) {
    var self = this;

    self.value = value;
    self.name = CinchApp.bidNames[value] || value.toString(); //If bid name exists for value use it, otherwise use value
    self.isValid = ko.computed(function() {
        if(self.value === CinchApp.bids.pass) {
            //Can always pass unless you're the dealer and everyone else has passed
            return parentViewModel.isActivePlayer() &&
                !(parentViewModel.dealer() === CinchApp.players.south && parentViewModel.highBid() <= CinchApp.bids.pass);
        }
        else if(self.value === CinchApp.bids.cinch) {
            //Can always bid Cinch if you're the dealer
            return parentViewModel.isActivePlayer() &&
                (parentViewModel.highBid() < CinchApp.bids.cinch || parentViewModel.dealer() === CinchApp.players.south);
        }
        else {
            return parentViewModel.isActivePlayer() && parentViewModel.highBid() < self.value;
        }
    });
    self.submit = function() {
        CinchApp.socket.emit('bid', self.value);
    };
}
