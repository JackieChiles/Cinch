import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['card-image'],
  intl: Ember.inject.service(),

  // Required parameter with 'suit' and 'rank' properties and/or 'faceDown' boolean
  card: null,
  src: Ember.computed('card', function () {
    const card = this.get('card');
    return card.faceDown ? '/card-images/b1fv.png' : `/card-images/${card.rank}${card.suit}.png`;
  }),
  alt: Ember.computed('card', function () {
    const card = this.get('card');
    return card.faceDown ? this.get('intl').t('faceDownCard') : `${card.rank}${card.suit}`;
  })
});
