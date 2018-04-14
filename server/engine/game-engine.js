const Game = require('./game');

module.exports = {
  // Games currently in progress; key is ID, value is game object
  activeGames: {},

  // Key is userId, value is gameId
  gamesByUser: {},

  // Add a game ID to the user's list in the gamesByUser hash when they join
  addGameToUserList(userId, gameId) {
    const userGames = this.gamesByUser[userId] || [];
    userGames.push(gameId);
    this.gamesByUser[userId] = userGames;
  },

  // Initialize and start a new game
  startNew(data, io) {
    const newGame = new Game(data, io);
    const userId = data.user.id;

    newGame.join('south', data.user); // TODO move inside constructor?
    this.activeGames[newGame.id] = newGame;
    this.addGameToUserList(userId, newGame.id);

    console.log(`New game ${newGame.id} started by ${userId}`);

    return newGame.getGameState(userId);
  },

  // All players have left game, so destroy it
  tearDownGame(gameId) {
    console.log(`Tearing down game ${gameId}`);
    delete this.activeGames[gameId];
  },

  // Join a player to an existing game
  // TODO handle invalid seat selection
  join(data) {
    console.log(`User '${data.user.name}' (${data.user.id}) attempting to join game '${data.gameId}' in position '${data.position}'`);
    const game = this.getGame(data.gameId);

    if (game) {
      console.log('Found game to join\n  User: ', data.user, '\n  Seat: ', data.position);
      this.addGameToUserList(data.user.id, data.gameId);
      return game.join(data.position, data.user);
    }

    return {};
  },

  // User disconnects; kick them from all games
  disconnect(userId) {
    const userGames = this.gamesByUser[userId];

    if (userGames) {
      userGames.forEach(gameId => this.leave(userId, gameId));
    }

    delete this.gamesByUser[userId];
  },

  // User leaves a game
  leave(userId, gameId) {
    const game = this.activeGames[gameId];

    console.log(`User ${userId} is leaving game ${gameId}`);

    if (game) {
      // Game's "leave" function returns true if all players have left the game
      if (game.leave(userId)) {
        this.tearDownGame(gameId);
      }

      const gamesForUser = this.gamesByUser[userId];

      if (gamesForUser) {
        const indexForUser = gamesForUser.indexOf(gameId);

        if (indexForUser > -1) {
          gamesForUser.splice(indexForUser, 1);
        }
      }
    }
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
    return Object.keys(this.activeGames).map(id => this.activeGames[id].getGameState());
  },

  // TODO handle no matching game found
  getGame(id) {
    return this.activeGames[id];
  }
};
