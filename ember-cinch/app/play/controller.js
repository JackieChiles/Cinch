import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller(),

  user: Ember.computed.reads('application.user'),
  game: Ember.computed.reads('model'),

  setup() {
    const socket = this.get('application.socket');

    // TODO handle request errors
    socket.on('join', data => {
      Ember.Logger.log('User joined the game', data);
      this.set(`game.${data.position}`, data.user);
    });

    socket.on('start', data => {
      Ember.Logger.log('Game is starting', data);

      const hands = this.get('game.hands');
      hands[this.get('application.user.id')] = data.myHand;
      this.set('game.hands', hands);
      this.set('game.phase', data.phase);
    });
  },

  teardown() {
    const socket = this.get('application.socket');
    socket.off('join');
    socket.off('start');
    socket.off('bid');
    socket.off('play');
  },

  init() {
    this._super(...arguments);

    // TODO turn off handlers after navigating away
    this.setup();
  }
});
