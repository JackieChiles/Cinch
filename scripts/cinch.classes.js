// Classes (invoked with new keyword only)

//Represents a single joinable game, as listed in the lobby
function Game(name, number, isFull) {
    var self = this;

    self.name = name;
    self.number = number;
    self.isFull = ko.observable(isFull);

    self.join = function() { // Only called when joining existing game, not ICW new
        CinchApp.socket.emit('join', number, function(msg) {
	        CinchApp.viewModel.curRoom(msg.roomNum);
                CinchApp.viewModel.activeView(CinchApp.views.game);
		if (msg.roomNum != 0) {
		    console.log('seatChart: ', msg.seatChart);///reminder to implement seatChart
		    CinchApp.socket.$events.users(msg.users);
		    CinchApp.socket.$events.seatChart(msg.seatChart);
		}
	});
    };
}

function Player(name, number) {
    var self = this;

    self.name = ko.observable(name);
    self.number = number;
    self.active = ko.observable(false);
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

        cardImage.src = self.imagePath;
        
        cardImage.onload = function() {
            CinchApp.viewModel.cardImagesInPlay[player] = new CardAnimation(cardImage, player);
        };
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
