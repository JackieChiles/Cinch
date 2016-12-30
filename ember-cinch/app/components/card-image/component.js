import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['card-image'],

  // Required parameter with 'suit' and 'rank' properties
  card: null,
  src: Ember.computed('card', function () {
    const card = this.get('card');
    return `/card-images/${card.rank}${card.suit}.png`;
  }),
  alt: Ember.computed('card', function () {
    const card = this.get('card');
    return `${card.rank}${card.suit}`;
  })
});
