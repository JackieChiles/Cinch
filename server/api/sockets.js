let io; 

exports.init = server => {
  io = require('socket.io')(server);

  io.on('connection', socket => {
    console.log('Client connected');

    // User starts or joins a game
    socket.on('join', gameId => {
      console.log(`User joined game socket channel ${gameId}`);
      socket.join(gameId);
    });
  });
};

exports.io = io;
