const colors = require('./colors');
const animals = require('./animals');
const rand = require('random-item-in-array');
const uuid = require('uuid/v4');

// Key is public user ID, value is socket ID
const socketUserHash = {};

exports.getAnonymousName = function () {
   return `${rand(colors)} ${rand(animals)}`;
};

// Returns a new user object
exports.getNewUser = function (socket, username) {
  const id = uuid();

  socketUserHash[id] = socket.id;

  return {
    name: username || exports.getAnonymousName(),
    id
  };
};

// Returns the socket ID for the given public user ID
exports.getSocketId = function (userId) {
  return socketUserHash[userId];
};

// Returns the public user ID for the given socket ID
// TODO handle user not found
exports.getUserId = function (socketId) {
  // TODO don't do this as it will be O(n) n = number of users
  return Object.keys(socketUserHash).filter(userId => socketUserHash[userId] === socketId)[0];
};

exports.updateUsername = function (socketId, name) {
  const user = exports.getUserId(socketId);

  if (user) {
    user.name = name;
  }
};

exports.disconnectUser = function (socketId) {
  delete socketUserHash[exports.getUserId(socketId)];
};
