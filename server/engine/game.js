const uuid = require('uuid/v4');
const shuffle = require('shuffle-array');
const ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
const suits = ['C', 'D', 'H', 'S'];
const HAND_SIZE = 9;

// Generates and shuffles a new 52-card deck
const getNewDeck = () => shuffle(suits.reduce((deck, suit) => ranks.reduce((cards, rank) => (cards.push({ rank, suit }), cards), deck), []));
                                

/*
  Game class

  initialState will evenutually contain agent selections and such
*/
function Game(initialState) {
  this.id = uuid();
  this.north = initialState ? initialState.north : null;
  this.east = initialState ? initialState.east : null;
  this.south = initialState ? initialState.south : null;
  this.west = initialState ? initialState.west : null;

  // Array of cards in deck in their current order
  this.deck = getNewDeck();

  console.log(this.deck);

  // Key is user ID, value is array of cards
  this.hands = {};

  // Returns public game state for this game
  // If user ID is passed that matches one in-game, that user's hand will be included as well
  this.getGameState = function (userId) {
    const state = {
      id: this.id,
      north: this.north,
      east: this.east,
      south: this.south,
      west: this.west,
      hands: {}
    };

    console.log(`Looking for hand in game state for user ${userId}. Current hands:\n`, this.hands);

    if (userId && this.hands[userId]) {
      console.log(`Found hand in game state for user ${userId} `, this.hands[userId]);
      state.hands[userId] = this.hands[userId];
    }

    return state;
  };

  // Generates a new hand of HAND_SIZE
  this.getNewHand = function() {
    return this.deck.splice(-HAND_SIZE)
  };

  // Join a user to an unoccupied seat
  this.join = function (seat, user) {
    if (seat && user && !this[seat]) {
      this[seat] = user;
      this.hands[user.id] = this.getNewHand();
      console.log('User join successful. Hand generated\n', this.hands[user.id], '\nNew deck length ', this.deck.length);

      return this.getGameState(user.id);
    }

    console.log('User join unsuccessful');
  };
};

module.exports = Game;
