import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['card-image'],
  classNameBindings: ['actionable', 'cssClass'],
  intl: Ember.inject.service(),

  // Parameter, optional, can be 'rotate90', 'rotate180', or 'rotate270' to rotate image
  cssClass: null,

  // Parameter, optional, fired when image is clicked with card as parameter
  onClick: null,

  _onClick(card) {
    Ember.Logger.log('_onClick of card-image', card);
    const action = this.get('onClick');
    if (action) {
      action(card);
    }
  },

  // Parameter with 'suit' and 'rank' properties and/or 'faceDown' boolean
  card: null,

  actionable: Ember.computed.bool('onClick'),

  src: Ember.computed('card', function () {
    const card = this.get('card');
    return card.faceDown ? '/card-images/b1fv.png' : `/card-images/${card.rank}${card.suit}.png`;
  }),

  alt: Ember.computed('card', function () {
    const card = this.get('card');
    return card.faceDown ? this.get('intl').t('faceDownCard') : `${card.rank}${card.suit}`;
  })
});
