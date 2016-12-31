const Game = require('./game');
const io = require('../api/sockets').io;

module.exports = {
  // Games currently in progress
  activeGames: [],

  // Initialize and start a new game
  startNew(data) {
    const newGame = new Game({}, io);
    newGame.join('south', data.user);
    this.activeGames.push(newGame);

    console.log(`New game '${newGame.id}' started`);

    return newGame.getGameState(data.user.id);
  },

  // Join a player to an existing game
  // TODO handle invalid seat selection
  // TODO handle no matching game found
  join(data) {
    console.log(`User '${data.user.name}' (${data.user.id}) attempting to join game '${data.gameId}' in seat '${data.seat}'`);
    const game = this.activeGames.filter(game => game.id === data.gameId)[0];

    if (game) {
      console.log('Found game to join\n  User: ', data.user, '\n  Seat: ', data.seat);
      return game.join(data.seat, data.user);
    }

    return {};
  },

  // Get a list of public game state for all active games
  getGameList() {
    return this.activeGames.map(game => game.getGameState());
  }
};
