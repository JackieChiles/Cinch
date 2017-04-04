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

      socket.on('initialize', username => {
        const user = userManager.getNewUser(socket, username);
        socket.emit('connection-success', user);
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

        // Send game data to user
        socket.emit('join-success', game);
      });

      // User makes a bid
      socket.on('bid', data => gameEngine.bid(userManager.getUserId(socket.id), data));

      // User makes a play
      socket.on('play', data => gameEngine.play(userManager.getUserId(socket.id), data));
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
