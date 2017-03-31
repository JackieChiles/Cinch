import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['team-score'],
  intl: Ember.inject.service(),

  // Parameter, required, game object
  game: null,

  // Parameter, required, team score
  score: 0,

  // Parameter, required, player position string
  firstPosition: null,

  firstPlayer: Ember.computed('firstPosition', 'game', function() {
    return this.get(`game.${this.get('firstPosition')}`);
  }),

  // Parameter, required, player position string
  secondPositino: null,

  secondPlayer: Ember.computed('secondPosition', 'game', function() {
    return this.get(`game.${this.get('secondPosition')}`);
  }),

  _getPositionBid(position) {
    const bid = this.get('game.currentBids').find(bid => bid.position === position);
    const intl = this.get('intl');
    const bidNames = [
      intl.t('bids.pass'),
      intl.t('bids.one'),
      intl.t('bids.two'),
      intl.t('bids.three'),
      intl.t('bids.four'),
      intl.t('bids.cinch')
    ];
      
    return bid && bidNames[bid.value];
  },

  firstBid: Ember.computed('game.currentBids', 'firstPosition', function () {
    return this._getPositionBid(this.get('firstPosition'));
  }),

  secondBid: Ember.computed('game.currentBids', 'secondPosition', function () {
    return this._getPositionBid(this.get('secondPosition'));
  })
});
