const colors = require('./colors');
const animals = require('./animals');
const rand = require('random-item-in-array');
const uuid = require('uuid/v4');

const getAnonymousName = function () {
   return `${rand(colors)} ${rand(animals)}`;
};

// Key is public user ID, value is socket ID
const socketUserHash = {};

// Returns a new user object
exports.getNewUser = function (socket) {
  const id = uuid();

  socketUserHash[id] = socket.id;

  return {
    name: getAnonymousName(),
    id
  };
};

// Returns the socket ID for the given public user ID
exports.getSocketId = function (userId) {
  return socketUserHash[userId];
};


// Returns the public user ID for the given socket ID
exports.getUserId = function (socketId) {
  // TODO don't do this as it will be O(n) n = number of users
  return Object.keys(socketUserHash).filter(userId => socketUserHash[userId] === socketId)[0];
};
