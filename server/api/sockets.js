exports.init = server => {
  const io = require('socket.io')(server);

  io.on('connection', socket => {
    console.log('Client connected');
  });
};
