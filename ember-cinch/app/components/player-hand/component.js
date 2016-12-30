import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['player-hand'],

  // Parameter, user object with 'id' and 'name'
  user: null,

  // Parameter, array of cards with 'rank' and 'suit' properties
  cards: [
    { rank: '2', suit: 'S' },
    { rank: '3', suit: 'S' },
    { rank: '4', suit: 'S' },
    { rank: '5', suit: 'S' },
    { rank: '6', suit: 'S' },
    { rank: '7', suit: 'S' },
    { rank: '8', suit: 'S' },
    { rank: '9', suit: 'S' },
    { rank: 'T', suit: 'S' },
    { rank: 'J', suit: 'S' }
  ]
});
