const Game = require('./game');

module.exports = {
  // Games currently in progress
  activeGames: [], // TODO make this hash instead?

  // Initialize and start a new game
  startNew(data, io) {
    const newGame = new Game(data, io);
    newGame.join('south', data.user); // TODO move inside constructor?
    this.activeGames.push(newGame);

    console.log(`New game ${newGame.id} started by ${data.user.id}`);

    return newGame.getGameState(data.user.id);
  },

  // Join a player to an existing game
  // TODO handle invalid seat selection
  join(data) {
    console.log(`User '${data.user.name}' (${data.user.id}) attempting to join game '${data.gameId}' in position '${data.position}'`);
    const game = this.getGame(data.gameId);

    if (game) {
      console.log('Found game to join\n  User: ', data.user, '\n  Seat: ', data.position);
      return game.join(data.position, data.user);
    }

    return {};
  },

  // User makes a bid
  bid(userId, data) {
    return this.getGame(data.gameId).bid(userId, data.value);
  },

  // User makes a play
  play(userId, data) {
    return this.getGame(data.gameId).play(userId, data.card);
  },

  // Get a list of public game state for all active games
  getGameList() {
    return this.activeGames.map(game => game.getGameState());
  },

  // TODO handle no matching game found
  getGame(id) {
    return this.activeGames.filter(game => game.id === id)[0];
  }
};
