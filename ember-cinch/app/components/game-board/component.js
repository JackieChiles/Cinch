import Ember from 'ember';

const HAND_SIZE = 9;

// Generates a face-down hand of cards for hands hidden from the current user
const generateFaceDownHand = () => {
  const hand = [];

  for (let index = 0; index < HAND_SIZE; index++) {
    hand.push({ faceDown: true });
  }

  return hand;
};

export default Ember.Component.extend({
  classNames: ['flex', 'layout-column', 'layout-align-center', 'game-board'],
  intl: Ember.inject.service(),

  // TODO move to util or something
  bidNames: null,

  // Parameter, game object
  game: null,

  // Parameter, user object
  currentUser: null,

  // Parameter, bid action, single argument is bid value
  bid() {},

  // Returns current bid name for the given position
  getBidName(position) {
    const bid = this.get('game.currentBids').filter(bid => bid.position === position)[0];

    if (bid) {
      return this.get('bidNames')[bid.value];
    }
  },

  isBidPhase: Ember.computed.equal('game.phase', 'bid'),

  isMyBid: Ember.computed('game.activePlayer', 'currentUserPosition', function () {
    return this.get('game.activePlayer') === this.get('currentUserPosition');
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

  isCurrentUserInGame: Ember.computed.bool('currentUserPosition'),

  // Game board is viewed from this user's perspective
  self: Ember.computed('game', 'selfPosition', function () {
    return this.get(`game.${this.get('selfPosition')}`);
  }),

  // Hand for "current perspective" user
  selfHand: Ember.computed('game', 'isCurrentUserInGame', 'self', function () {
    if (this.get('isCurrentUserInGame')) {
      return this.get('game.hands')[this.get('self.id')];
    }

    return generateFaceDownHand();
  }),

  selfBid: Ember.computed('game', 'selfPosition', function () {
    return this.getBidName(this.get('selfPosition'));
  }),

  partnerPosition: Ember.computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'south' :
      currentUserPosition === 'east' ? 'west' :
      currentUserPosition === 'west' ? 'east' :
      'north';
  }),

  partner: Ember.computed('game', 'partnerPosition', function () {
    return this.get(`game.${this.get('partnerPosition')}`);
  }),

  partnerHand: generateFaceDownHand(),

  partnerBid: Ember.computed('game', 'partnerPosition', function () {
    return this.getBidName(this.get('partnerPosition'));
  }),

  leftOpponentPosition: Ember.computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'east' :
      currentUserPosition === 'east' ? 'south' :
      currentUserPosition === 'west' ? 'north' :
      'west';
  }),

  leftOpponent: Ember.computed('game', 'leftOpponentPosition', function () {
    return this.get(`game.${this.get('leftOpponentPosition')}`);
  }),

  leftOpponentHand: generateFaceDownHand(),

  leftOpponentBid: Ember.computed('game', 'leftOpponentPosition', function () {
    return this.getBidName(this.get('leftOpponentPosition'));
  }),

  rightOpponentPosition: Ember.computed('currentUserPosition', function () {
    const currentUserPosition = this.get('currentUserPosition');
    return currentUserPosition === 'north' ? 'west' :
      currentUserPosition === 'east' ? 'north' :
      currentUserPosition === 'west' ? 'south' :
      'east';
  }),

  rightOpponent: Ember.computed('game', 'rightOpponentPosition', function () {
    return this.get(`game.${this.get('rightOpponentPosition')}`);
  }),

  rightOpponentHand: generateFaceDownHand(),

  rightOpponentBid: Ember.computed('game', 'rightOpponentPosition', function () {
    return this.getBidName(this.get('rightOpponentPosition'));
  }),

  init() {
    this._super(...arguments);

    const intl = this.get('intl');
    this.set('bidNames', [
      intl.t('bids.pass'),
      intl.t('bids.one'),
      intl.t('bids.two'),
      intl.t('bids.three'),
      intl.t('bids.four'),
      intl.t('bids.cinch')
    ]);
  }
});
