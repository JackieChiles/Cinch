// Main namespace

var CinchApp = {
    //Constants
    gameModeNew: 0,
    numPlayers: 4,
    numTeams: 2,
    numPossibleBids: 6,
    boardClearDelay: 1300,
    playSurfaceWidth: 290,
    playSurfaceHeight: 245,
    cardImageWidth: 72,
    cardImageHeight: 96,
    cardEdgeOffset: 5,
    cardImageDir: 'images/',
    cardImageExtension: '.png',
    noneBidDisplay: '-',
    defaultPlayerName: 'Anonymous',
    systemUser: 'System',
    faceDownCard: function() {
        //Represents face-down cards in other players' hands, used in KO arrays for those hands
        //You may not pay 3 colorless to morph
        
        return {
            vertImagePath: this.cardImageDir + 'b1fv' + this.cardImageExtension,
            horizImagePath: this.cardImageDir + 'b1fh' + this.cardImageExtension
        };
    },
    suits: ['C', 'D', 'H', 'S'],
    suitNames: ['Clubs', 'Diamonds', 'Hearts', 'Spades'],
    ranks: ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'],
    bidEnum: {
        none: -1,
        pass: 0,
        one: 1,
        two: 2,
        three: 3,
        four: 4,
        cinch: 5
    },
    gameModeEnum: {
        play: 1,
        bid: 2
    },
    playerEnum: {
        south: 0,
        west: 1,
        north: 2,
        east: 3
    },
    bidNames: [
        'Pass',
        'One',
        'Two',
        'Three',
        'Four',
        'Cinch'
    ],
    responseModeEnum: {
        holding: 0,
        running: 1
    },
    pointTypes: {
        high: 'h',
        low: 'l',
        jack: 'j',
        game: 'g'
    },
    messageTypes: { //Types of chat messages
        normal: 0,
        error: 1
    },
    
    //Other
    viewModel: null, //Knockout viewmodel
    responseCount: 0, //Development
    isDebugMode: true,
    guid: 0,
    cardImagesInPlay: [], //Tracks card images for animation purposes
    trickWinner: -1, //Relative to client (self is always CinchApp.playerEnum.south)
    
    //Function queue: all GET responses go here to be processed once app is in 'running' mode
    //Any other functions can be added here as needed
    responseQueue: [],    
    processing: false, //Flag for ProcessQueue
    secondaryActionQueue: [], //Actions with dependencies go here to be run last
    lockCount: 0, //count for number of active animations
    
    //If "ravenholm" is in the URL, app must be running on production server, so use that URL, otherwise use dev. URL
    serverUrl: window.location.href.indexOf('ravenholm') > -1
        ? 'http://ravenholm.dyndns.tv:2424' //Legend url
        : 'http://localhost:2424', //Development URL
    actions: {
        actvP: function (update) { CinchApp.viewModel.activePlayer(serverToClientPNum(update.actvP)); },
        addC: function (update) {
            //Must wait until after other handlers are called in case cards need to be removed first (from playC handler)      
            CinchApp.secondaryActionQueue.push(function () {
                var i = 0;
                var j = 0;
                var cardsToAdd = update.addC;
                
                CinchApp.viewModel.encodedCards(cardsToAdd);
                
                //We have to manually trigger an update of the page so JQM catches all the bindings
                $('#game-page').trigger('create');
                
                //Populate other players' hands with face-down cards
                //Can use cardsToAdd.length to get number of cards that should be in each player's hand
                for(i = 0; i < cardsToAdd.length; i++) {
                    for(j = 1; j < CinchApp.numPlayers; j++) { //Skip index zero (client player, face-up hand)
                        CinchApp.viewModel.cardsInAllHands[j].push(CinchApp.faceDownCard());
                    }
                }
            });
        },
        aList: function(update) {
            CinchApp.viewModel.ai(update.aList);
            
            //Initialize the UI for the AI agents
            $('#ai-list .ai').listview();
        },
        bid: function (update) { CinchApp.viewModel.currentBids[update.actor](update.bid); },
        dlr: function (update) { CinchApp.viewModel.dealer(serverToClientPNum(update.dlr)); },
        err: function (update) { outputErrorMessage(update.err); },
        gList: function (update) {
            var i = 0;
            var gList = update.gList;
            var games;
            
            //Clear out the old games
            CinchApp.viewModel.games([]);
            
            //Add the new games
            for(i = 0; i < gList.length; i++) {
                CinchApp.viewModel.games.push(new Game(gList[i]));
            }
            
            //Render the newly added UI
            $('#lobby-page').trigger('create');
            
            //But wait! The jqmButtonEnabled bindings have already been applied, trigger them again
            games = CinchApp.viewModel.games();
            
            for(i = 0; i < games.length; i++) {
                games[i].players.valueHasMutated();
            }
        },
        mode: function (update) {
            //The rest of the hand-end processing is done through Knockout subscriptions, etc.
            CinchApp.viewModel.matchPoints(update.mp || []);
            CinchApp.viewModel.gamePoints(update.gp || []);
            CinchApp.viewModel.gameMode(update.mode);
        },
        msg: function (update) { outputMessage(update.msg, CinchApp.viewModel.playerNames[serverToClientPNum(parseInt(update.uNum, 10))]); },
        names: function (update) {
            var i = 0;
            var names = update.names;
            
            for(i = 0; i < names.length; i++) {
                //Store name
                CinchApp.viewModel.playerNames[serverToClientPNum(names[i].pNum)] = names[i].name;
                
                //Announce player's arrival
                outputMessage('Player ' + names[i].name + ' is now in the game.', CinchApp.systemUser);
            }
        },
        playC: function (update) { CinchApp.viewModel.playCard(update.playC, update.actor); },
        pNum: function (update) { CinchApp.viewModel.myPlayerNum(update.pNum); },
        remP: function (update) {
            CinchApp.trickWinner = serverToClientPNum(update.remP);

            //Must wait until 'playC' is handled
            CinchApp.secondaryActionQueue.push(function () {
                CinchApp.viewModel.lockBoard(); //Board is unlocked in cinch.animation.js:animateBoardClear()

                //Wait a bit so the ending play can be seen
                setTimeout(function () {
                    finishClearingBoard();
                }, CinchApp.boardClearDelay);
            });
        }, //TODO: use update.playC here?
        sco: function (update) { CinchApp.viewModel.gameScores(update.sco); },
        trp: function (update) { CinchApp.viewModel.trump(update.trp); },
        uid: function (update) {
            //Don't start long-polling until server gives valid guid
            $.mobile.changePage( '#game-page', { transition: 'slide'} );
            CinchApp.guid = update.uid;
            CinchApp.viewModel.unlockBoard();
            startLongPoll();
        },
        win: function (update) {
            //Game is over, so update match and game points and winner value
            //This will trigger the hand-end dialog with the game-end information enabled
            CinchApp.viewModel.matchPoints(update.mp || []);
            CinchApp.viewModel.gamePoints(update.gp || []);
            CinchApp.viewModel.winner(update.win);
        }
    }
};