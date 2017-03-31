import Ember from 'ember';

const HAND_SIZE = 9;

// Generates a face-down hand of cards for hands hidden from the current user
const generateFaceDownHand = () => {
  const hand = [];

  for (let index = 0; index < HAND_SIZE; index++) {
    hand.push({ faceDown: true });
  }

  return hand;
};

export default Ember.Component.extend({
  classNames: ['player-hand'],

  // Parameter, game object
  game: null,

  // Parameter, position of player
  position: '',

  // Parameter, optional, action to fire when card is clicked with card as parameter
  cardAction() {},

  user: Ember.computed('game', 'position', function () {
    return this.get(`game.${this.get('position')}`);
  }),

  cards: Ember.computed('game', 'user', function () {
    return this.get('game.hands')[this.get('user.id')] || generateFaceDownHand();
  })
});
