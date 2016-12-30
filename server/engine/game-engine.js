const Game = require('./game').Game;

exports.engine = {
  // Games currently in progress
  activeGames: [],

  // Initialize and start a new game
  startNew(data) {
    const newGame = new Game({
      south: data.user
    });
    this.activeGames.push(newGame);

    console.log(`New game '${newGame.id}' started`);

    return newGame.getGameState();
  },

  // Join a player to an existing game
  // TODO handle invalid seat selection
  // TODO handle no matching game found
  join(data) {
    console.log(`User '${data.user.name}' (${data.user.id}) attempting to join game '${data.gameId}' in seat '${data.seat}'`);
    const game = this.activeGames.filter(game => game.id === data.gameId)[0];

    if (game && !game[data.seat]) {
      game[data.seat] = data.user;
      return game;
    }

    return {};
  },

  // Get a list of public game state for all active games
  getGameList() {
    return this.activeGames.map(game => game.getGameState());
  }
};