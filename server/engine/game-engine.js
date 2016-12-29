const Game = require('./game').Game;

exports.engine = {
  // Games currently in progress
  activeGames: [],

  // Initialize and start a new game
  startNew(data) {
    const newGame = new Game(data);
    this.activeGames.push(newGame);

    console.log(`New game '${newGame.id}' started`);

    return newGame.getGameState();
  },

  // Get a list of public game state for all active games
  getGameList() {
    return this.activeGames.map(g => g.getGameState());
  }
};
