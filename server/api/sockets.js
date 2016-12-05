exports.init = server => {
  const io = require('socket.io')(server);
  //const gameEngine = require('../engine/gameEngine.js');

  io.on('connection', socket => {
    console.log('Client connected');
  });
};
