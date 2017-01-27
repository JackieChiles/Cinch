import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller(),

  agents: Ember.computed.reads('model'),

  startGame() {
    // TODO send agent selections
    this.get('application.socket').emit('new', {
      user: this.get('application.user')
    });
  },

  init() {
    this._super(...arguments);

    // TODO handle request error
    // TODO turn off handler after navigating away
    this.get('application.socket').on('new-success', game => this.transitionToRoute('play', game));
  }
});
