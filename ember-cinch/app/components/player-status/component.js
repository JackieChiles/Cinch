import { computed } from '@ember/object';
import { inject as service } from '@ember/service';
import Component from '@ember/component';

export default Component.extend({
  classNames: ['player-status'],
  intl: service(),

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

  player: computed('position', 'game', function() {
    return this.get(`game.${this.get('position')}`);
  }),

  bid: computed('game.currentBids', 'position', function () {
    return this._getPositionBid(this.get('position'));
  }),

  playerWonBid: computed('position', 'game.{phase,currentHandWinningBid.position}', function () {
    return this.get('game.phase') === 'play' && this.get('position') === this.get('game.currentHandWinningBid.position');
  })
});
