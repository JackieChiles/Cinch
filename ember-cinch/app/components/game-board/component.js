import { computed, get } from '@ember/object';
import { equal } from '@ember/object/computed';
import { inject as service } from '@ember/service';
import Component from '@ember/component';

export default Component.extend({
  classNames: ['flex', 'layout-column', 'layout-align-center', 'game-board'],
  intl: service(),

  // Parameter, game object
  game: null,

  // Parameter, user object
  currentUser: null,

  // Parameter, bid action, single argument is bid value
  bid() {},

  // Parameter, play action, single argument is card
  play() {},

  // Returns current card in play for the given position
  getCardInPlay(position) {
    const currentPlays = this.get('game.currentPlays');

    if (!currentPlays) {
      return;
    }

    const play = currentPlays.filter(play => play.position === position)[0];

    if (play) {
      return play.card;
    }
  },

  isBidPhase: equal('game.phase', 'bid'),
  isGameOver: equal('game.phase', 'postgame'),

  isMyBid: computed('game.activePlayer', 'currentUserPosition', function () {
    return this.get('game.activePlayer') === this.get('currentUserPosition');
  }),

  // Array containing the two positions of the winnning players, falsey if game not over
  winningPositions: computed('game.gameWinner', function () {
    const gameWinner = this.get('game.gameWinner');
    return gameWinner && gameWinner.split('_');
  }),

  // Score of the winning team if game over, otherwise falsey
  winningScore: computed('game.gameWinner', function () {
    const gameWinner = this.get('game.gameWinner');
    return gameWinner && (gameWinner.includes('north') ? this.get('game.nsScore') : this.get('game.ewScore'));
  }),

  // Position of current user in game. Will be null if current user is not joined to this game.
  currentUserPosition: computed('game.{north,east,south,west}', function () {
    const game = this.get('game');
    const currentUser = this.get('currentUser');

    if (game && currentUser) {
      return [
        'north',
        'south',
        'east',
        'west'
      ].filter(position => get(game, `${position}.id`) === currentUser.id)[0] || null;
    }

    return null;
  }),

  // Game board is viewed from this position. Defaults to south if current user is not in game.
  selfPosition: computed('currentUserPosition', function () {
    return this.get('currentUserPosition') || 'south';
  }),

  selfCard: computed('game', 'selfPosition', function () {
    return this.getCardInPlay(this.get('selfPosition'));
  }),

  partnerPosition: computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'south' :
      currentUserPosition === 'east' ? 'west' :
      currentUserPosition === 'west' ? 'east' :
      'north';
  }),

  partnerCard: computed('game', 'partnerPosition', function () {
    return this.getCardInPlay(this.get('partnerPosition'));
  }),

  leftOpponentPosition: computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'east' :
      currentUserPosition === 'east' ? 'south' :
      currentUserPosition === 'west' ? 'north' :
      'west';
  }),

  leftOpponentCard: computed('game', 'leftOpponentPosition', function () {
    return this.getCardInPlay(this.get('leftOpponentPosition'));
  }),

  rightOpponentPosition: computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'west' :
      currentUserPosition === 'east' ? 'north' :
      currentUserPosition === 'west' ? 'south' :
      'east';
  }),

  rightOpponentCard: computed('game', 'rightOpponentPosition', function () {
    return this.getCardInPlay(this.get('rightOpponentPosition'));
  })
});
