const uuid = require('uuid/v4');

/*
  Game class

  Example initialState where a player has started a new game and selected an agent for 'west' seat, leaving 'north' and 'east' open

  {
    seats: {
      south: {
        playerId: 'a48f'
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

  // Returns public game state for this game
  this.getGameState = () => {
    return {
      id: this.id
    };
  };
};
