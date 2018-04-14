const gameEngine = require('../engine/game-engine');
const userManager = require('../users/user-manager');

let io;

module.exports = {
  init: server => {
    io = require('socket.io')(server);

    // Inbound socket messages
    io.on('connection', socket => {
      // Respond to the new user connection
      console.log(`Client connected with socket id ${socket.id}`);

      socket.on('initialize', (username, callback) => {
        const user = userManager.getNewUser(socket, username);
        callback(user);
      });

      socket.on('disconnect', () => {
        console.log(`Client disconnected with socket id ${socket.id}`);
        gameEngine.disconnect(userManager.getUserId(socket.id));
      });

      // User starts a new game
      socket.on('new', data => {
        console.log('New game requested', data);
        console.log(gameEngine);
        const game = gameEngine.startNew(data, module.exports);
        
        // Join user to socket room for new game
        socket.join(game.id);

        // Send new game data to user
        socket.emit('new-success', game);
      });

      // User joins an existing game
      socket.on('join', data => {
        const game = gameEngine.join(data);

        // Join user to socket room for new game
        socket.join(game.id);

        // TODO make this a callback response instead
        // Send game data to user
        socket.emit('join-success', game);
      });

      // User makes a bid
      socket.on('bid', data => gameEngine.bid(userManager.getUserId(socket.id), data));

      // User makes a play
      socket.on('play', data => gameEngine.play(userManager.getUserId(socket.id), data));

      // User requests a new generated username
      socket.on('generate-username', callback => {
        callback(userManager.getAnonymousName());
      });

      // User requests an update to their username
      // TODO emit to other users
      socket.on('update-username', (name, callback) => {
        userManager.updateUsername(socket.id, name);
        callback(name);
      });
    });
  },

  // Outbound socket messages
  bid(userId, data) {
    io.to(userManager.getSocketId(userId)).emit('bid', data);
  },

  play(userId, data) {
    io.to(userManager.getSocketId(userId)).emit('play', data);
  },

  joinSuccess(userId, data) {
    io.to(userManager.getSocketId(userId)).emit('join-success', data);
  },

  join(userId, data) {
    io.to(userManager.getSocketId(userId)).emit('join', data);
  }
};
