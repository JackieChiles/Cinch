const colors = require('./colors');
const animals = require('./animals');
const rand = require('random-item-in-array');
const uuid = require('uuid/v4');

const getAnonymousName = function () {
   return `${rand(colors)} ${rand(animals)}`;
};

// Key is socket ID, value is public user ID
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
exports.getUserSocketId = function (userId) {
  return socketUserHash[userId];
};
