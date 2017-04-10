import Ember from 'ember';

export default Ember.Component.extend({
  classNames: ['flex', 'layout-column', 'layout-align-center', 'game-board'],
  intl: Ember.inject.service(),

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

  isBidPhase: Ember.computed.equal('game.phase', 'bid'),
  isGameOver: Ember.computed.equal('game.phase', 'postgame'),

  isMyBid: Ember.computed('game.activePlayer', 'currentUserPosition', function () {
    return this.get('game.activePlayer') === this.get('currentUserPosition');
  }),

  // Array containing the two positions of the winnning players, falsey if game not over
  winningPositions: Ember.computed('game.gameWinner', function () {
    const gameWinner = this.get('game.gameWinner');
    return gameWinner && gameWinner.split('_');
  }),

  // Score of the winning team if game over, otherwise falsey
  winningScore: Ember.computed('game.gameWinner', function () {
    const gameWinner = this.get('game.gameWinner');
    return gameWinner && (gameWinner.includes('north') ? this.get('game.nsScore') : this.get('game.ewScore'));
  }),

  // Position of current user in game. Will be null if current user is not joined to this game.
  currentUserPosition: Ember.computed('game.{north,east,south,west}', function () {
    const game = this.get('game');
    const currentUser = this.get('currentUser');

    if (game && currentUser) {
      return [
        'north',
        'south',
        'east',
        'west'
      ].filter(position => Ember.get(game, `${position}.id`) === currentUser.id)[0] || null;
    }

    return null;
  }),

  // Game board is viewed from this position. Defaults to south if current user is not in game.
  selfPosition: Ember.computed('currentUserPosition', function () {
    return this.get('currentUserPosition') || 'south';
  }),

  selfCard: Ember.computed('game', 'selfPosition', function () {
    return this.getCardInPlay(this.get('selfPosition'));
  }),

  partnerPosition: Ember.computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'south' :
      currentUserPosition === 'east' ? 'west' :
      currentUserPosition === 'west' ? 'east' :
      'north';
  }),

  partnerCard: Ember.computed('game', 'partnerPosition', function () {
    return this.getCardInPlay(this.get('partnerPosition'));
  }),

  leftOpponentPosition: Ember.computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'east' :
      currentUserPosition === 'east' ? 'south' :
      currentUserPosition === 'west' ? 'north' :
      'west';
  }),

  leftOpponentCard: Ember.computed('game', 'leftOpponentPosition', function () {
    return this.getCardInPlay(this.get('leftOpponentPosition'));
  }),

  rightOpponentPosition: Ember.computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'west' :
      currentUserPosition === 'east' ? 'north' :
      currentUserPosition === 'west' ? 'south' :
      'east';
  }),

  rightOpponentCard: Ember.computed('game', 'rightOpponentPosition', function () {
    return this.getCardInPlay(this.get('rightOpponentPosition'));
  })
});
