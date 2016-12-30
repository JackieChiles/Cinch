import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['player-hand'],

  // Parameter, user object with 'id' and 'name'
  user: null,

  // Parameter, array of cards with 'rank' and 'suit' properties and/or 'faceDown' boolean
  cards: []
});
