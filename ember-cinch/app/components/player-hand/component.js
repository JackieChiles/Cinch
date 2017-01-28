import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['player-hand'],

  // Parameter, user object with 'id' and 'name'
  user: null,

  // Parameter, array of cards with 'rank' and 'suit' properties and/or 'faceDown' boolean
  cards: [],

  // Parameter, display text for current bid made by user, if any
  currentBid: null,

  // Parameter, optional, action to fire when card is clicked with card as parameter
  cardAction() {}
});
