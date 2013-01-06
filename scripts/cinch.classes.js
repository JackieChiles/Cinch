// Classes (invoked with new keyword only)

//TODO: encapsulate bidNames? (parameter, local variable, etc.)
//Represents a possible bid to be made by the player
function Bid(parentViewModel, value, validFunction) {
    var self = this;
    
    //actualValidFunction will be the passed function if available
    //Or, if parentViewModel is a valid CinchViewModel the default isValid function will be used
    //Otherwise, we're out of options- the bid is always valid
    var actualValidFunction =
        validFunction
        || (parentViewModel instanceof CinchViewModel
        ? function() { return parentViewModel.isActivePlayer() && parentViewModel.highBid() < value; }
        : function() { return true; });
    
    this.value = value;
    this.name = CinchApp.bidNames[value] || value.toString(); //If bid name exists for value use it, otherwise use value
    this.isValid = ko.computed(actualValidFunction);
    this.submit = function() {
        postData({ 'uid': CinchApp.guid, 'bid': self.value });
    };
}

//Represents a single playable card
function Card(encodedCard) {
    var numRanks = CinchApp.ranks.length;
    var suitIndex = Math.floor((encodedCard - 1) / numRanks);
    
    this.encoded = encodedCard;
    this.decoded = CinchApp.ranks[this.encoded - suitIndex * numRanks - 1] + CinchApp.suits[suitIndex];   
    this.imagePath = CinchApp.cardImageDir + this.decoded + CinchApp.cardImageExtension;
    
    //Development (really just an easter egg now, I guess ??? )
    this.imagePath =
        this.imagePath.indexOf('undefined') > 0 || this.imagePath.indexOf('NaN') > 0
        ? CinchApp.cardImageDir + 'undefined' + CinchApp.cardImageExtension
        : this.imagePath;
    
    this.play = function(player) {
        CinchApp.viewModel.lockBoard();
        
        var cardStartPosition = getStartPosition(player);
        var cardEndPosition = getEndPosition(player);
        
        var canvas = document.getElementById('play-surface');
        var context = canvas.getContext('2d');
        var cardImage = new Image();
        cardImage.src = this.imagePath;

        var cardGfx = new CardAnimation(cardImage, player);
        CinchApp.cardImagesInPlay[player] = cardGfx;
    };
    
    this.submit = function() {
        postData({'uid': CinchApp.guid, 'card': this.encoded});
    };
};

//Represents an available game in the lobby
function Game(gameObject) {
    var self = this;
    var i = 0;
    var players = [];
    
    for(i = 0; i < gameObject.plrs.length; i++) {
        players[gameObject.plrs[i].num] = gameObject.plrs[i];
    }
    
    self.number = gameObject.num;
    self.players = ko.observableArray(players);
    self.playerNames = ko.computed(function() {
        var names = [];
        var i = 0;
        var currentPlayer;
        
        for(i = 0; i < CinchApp.numPlayers; i++) {
            currentPlayer = self.players()[i];
            
            names.push(currentPlayer ? currentPlayer.name || CinchApp.defaultPlayerName : '-');
        }
        
        return names;
    });
    self.isOccupied = ko.computed(function() {
        var seats = [];
        var i;
        
        for(i = 0; i < CinchApp.numPlayers; i++) {
            //Coerce a boolean
            seats.push(self.players()[i] ? true : false);
        }
        
        return seats;
    });
    self.submitJoin = function(seat) {
        postData({
            join: self.number,
            pNum: seat,
            name: CinchApp.viewModel.username() || CinchApp.defaultPlayerName
        });
    };
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
};