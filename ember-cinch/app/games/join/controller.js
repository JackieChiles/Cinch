import Ember from 'ember';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),
  application: Ember.inject.controller(),

  game: Ember.computed.reads('model'),

  takeSeat(seat) {
    this.get('application.socket').emit('join', {
      // TODO can do user lookup server-side
      user: this.get('application.user'),
      gameId: this.get('game.id'),
      position: seat
    });
  },

  init() {
    this._super(...arguments);

    // TODO handle request error
    // TODO turn off handler after navigating away
    this.get('application.socket').on('join-success', game => this.transitionToRoute('play', game));
  }
});
