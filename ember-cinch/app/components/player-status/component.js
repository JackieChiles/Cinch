import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['player-status'],
  intl: Ember.inject.service(),

  // Parameter, required, game object
  game: null,

  // Parameter, required, player position string
  position: null,

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

  player: Ember.computed('position', 'game', function() {
    return this.get(`game.${this.get('position')}`);
  }),

  bid: Ember.computed('game.currentBids', 'position', function () {
    return this._getPositionBid(this.get('position'));
  })
});
