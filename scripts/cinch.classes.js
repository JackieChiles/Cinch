// Classes (invoked with new keyword only)

//Represents a single joinable game, as listed in the lobby
function Game(name, number) {
    var self = this;

    self.name = name;
    self.number = number;
    self.join = function() {
        CinchApp__.socket.emit('join', number);
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

        return CinchApp__.isNullOrUndefined(bid) ? '-' : CinchApp__.bidNames[bid];
    });    
}

//Represents a single message from an entity
function VisibleMessage(text, name, messageType) {
    var self = this;

    self.text = text;
    self.name = name;
    self.type = ko.observable(messageType || CinchApp__.messageTypes.normal);
    self.cssClass = ko.computed(function() {
        return self.type() === CinchApp__.messageTypes.error ? 'error-msg' : '';
    });
}

//Represents a single playable card
function Card(encodedCard) {
    var numRanks = CinchApp__.ranks.length;
    var suitIndex = Math.floor((encodedCard - 1) / numRanks);
    var self = this;
    
    self.encoded = encodedCard;
    self.decoded = CinchApp__.ranks[self.encoded - suitIndex * numRanks - 1] + CinchApp__.suits[suitIndex];   
    self.imagePath = CinchApp__.cardImageDir + self.decoded + CinchApp__.cardImageExtension;
    
    self.play = function(player) {
        CinchApp__.viewModel.addAnimation(function() {
            var cardImage = new Image();

            cardImage.src = self.imagePath;
            CinchApp__.viewModel.cardImagesInPlay[player] = new CardAnimation(cardImage, player);
        });
    };
    
    self.submit = function() {
        CinchApp__.socket.emit('play', self.encoded);
    };
}

//Represents a possible bid to be made by the player
function Bid(parentViewModel, value) {
    var self = this;

    self.value = value;
    self.name = CinchApp__.bidNames[value] || value.toString(); //If bid name exists for value use it, otherwise use value
    self.isValid = ko.computed(function() {
        if(self.value === CinchApp__.bids.pass) {
            //Can always pass unless you're the dealer and everyone else has passed
            return parentViewModel.isActivePlayer() &&
                !(parentViewModel.dealer() === CinchApp__.players.south && parentViewModel.highBid() <= CinchApp__.bids.pass);
        }
        else if(self.value === CinchApp__.bids.cinch) {
            //Can always bid Cinch if you're the dealer
            return parentViewModel.isActivePlayer() &&
                (parentViewModel.highBid() < CinchApp__.bids.cinch || parentViewModel.dealer() === CinchApp__.players.south);
        }
        else {
            return parentViewModel.isActivePlayer() && parentViewModel.highBid() < self.value;
        }
    });
    self.submit = function() {
        CinchApp__.socket.emit('bid', self.value);
    };
}
