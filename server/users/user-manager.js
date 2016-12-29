const colors = require('./colors');
const animals = require('./animals');
const rand = require('random-item-in-array');
const uuid = require('uuid/v4');

const getAnonymousName = function () {
   return `${rand(colors)} ${rand(animals)}`;
};

exports.getNewUser = function () {
  return {
    name: getAnonymousName(),
    id: uuid()
  };
};
