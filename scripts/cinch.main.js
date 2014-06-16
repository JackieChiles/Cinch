//Main namespace
var CinchApp = {
    viewModel: null,
    socket: io.connect(location.protocol+'//'+location.hostname+":8088/cinch"),
    
    //Constants
    playSurfaceWidth: 290,
    playSurfaceHeight: 245,
    cardImageWidth: 72,
    cardImageHeight: 96,
    boardClearDelay: 1300,
    cardEdgeOffset: 5,
    numPlayers: 4,
    numTeams: 2,
    views: {
        home: 'home-page',
        lobby: 'lobby-page',
        ai: 'ai-page',
        handEnd: 'hand-end-page',
        game: 'game-page',
        seatSelect: 'seat-select-page'
    },
    chatContainers: {
        'lobby-page': 'lobby-page-chat',
        'hand-end-page': 'hand-end-page-chat',
        'game-page': 'game-page-chat'
    },
    players: {
        south: 0,
        west: 1,
        north: 2,
        east: 3
    },
    gameModes: {
        play: 1,
        bid: 2
    },
    messageTypes: { //Types of chat messages
        normal: 0,
        error: 1
    },
    ranks: ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'],
    suits: ['C', 'D', 'H', 'S'],
    suitNames: ['Clubs', 'Diamonds', 'Hearts', 'Spades'],
    cardImageDir: 'images/',
    cardImageExtension: '.png',
    bidNames: [
        'Pass',
        'One',
        'Two',
        'Three',
        'Four',
        'Cinch'
    ],
    bids: {
        none: -1,
        pass: 0,
        one: 1,
        two: 2,
        three: 3,
        four: 4,
        cinch: 5
    },
    pointTypes: {
        high: 'h',
        low: 'l',
        jack: 'j',
        game: 'g'
    },

    //Functions
    isNullOrUndefined: function(value) {
        return typeof value === 'undefined' || value === null;
    },
    serverToClientPNum: function(serverNum) {
        //Adjusts serverNum to match "client is South" perspective
        return (serverNum - CinchApp.viewModel.myPlayerNum() + CinchApp.numPlayers) % CinchApp.numPlayers;
    }
};
