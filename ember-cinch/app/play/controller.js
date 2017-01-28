import Ember from 'ember';

const PHASE_CHANGE_DELAY = 3000;

export default Ember.Controller.extend({
  application: Ember.inject.controller(),

  user: Ember.computed.reads('application.user'),
  game: Ember.computed.reads('model'),

  // Update the game state
  updateGame(game) {
    Ember.Logger.log('Updating game state');

    //TODO figure out phase delay
    /*
    // Update all except phase; leave a delay so final bids/plays can be shown
    const newPhase = game.phase;
    const oldGame = this.get('game');
    if (newPhase !== oldGame.phase) {
      game.phase = oldGame.phase;

      // TODO store timer variable
      Ember.run.later(() => this.set('game.phase', newPhase), PHASE_CHANGE_DELAY);
    }
    */

    this.set('game', game);
  },

  setup() {
    const socket = this.get('application.socket');

    // TODO handle request errors
    socket.on('join', data => {
      Ember.Logger.log('User joined the game');
      this.updateGame(data.game);
    });

    socket.on('start', data => {
      Ember.Logger.log('Game is starting');
/*
      const hands = this.get('game.hands');
      hands[this.get('application.user.id')] = data.myHand;
      this.set('game.hands', hands);
      this.set('game.phase', data.phase);
      */
      this.updateGame(data.game);
    });

    socket.on('bid', data => {/*
      this.set(`game.currentBids.${data.position}`, data.bidValue);
      this.set('game.activePlayer', data.activePlayer);

      // Delay phase change so all bids can be seen
      // TODO store timer variable
      Ember.run.later(() => this.set('game.phase', data.phase), PHASE_CHANGE_DELAY);*/
      this.updateGame(data.game);
    });
  },

  teardown() {
    const socket = this.get('application.socket');
    socket.off('join');
    socket.off('start');
    socket.off('bid');
    socket.off('play');
  },

  bid(value) {
    Ember.Logger.log('Bid made', value);
    this.get('application.socket').emit('bid', {
      gameId: this.get('game.id'),
      value
    });
  },

  play(card) {
    Ember.Logger.log('Play made', card);
    this.get('application.socket').emit('play', {
      gameId: this.get('game.id'),
      card
    });
  },

  init() {
    this._super(...arguments);

    // TODO turn off handlers after navigating away
    this.setup();
  }
});
