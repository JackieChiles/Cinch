const uuid = require('uuid/v4');

/*
  Game class

  Example initialState where a player has started a new game and selected an agent for 'west' seat, leaving 'north' and 'east' open

  {
    seats: {
      south: {
        user: {
          id: 'a48f',
          name: 'Jim'
        }
      },
      west: {
        agentId: '97ce'
      },
      north: {
      },
      south: {
      }
    }
  }
*/
exports.Game = function (initialState) {
  this.id = uuid();
  this.north = initialState.north;
  this.east = initialState.east;
  this.south = initialState.south;
  this.west = initialState.west;

  // Returns public game state for this game
  this.getGameState = () => {
    return {
      id: this.id,
      north: this.north,
      east: this.east,
      south: this.south,
      west: this.west
    };
  };
};
