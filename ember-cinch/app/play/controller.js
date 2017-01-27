import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller(),

  user: Ember.computed.reads('application.user'),
  game: Ember.computed.reads('model'),

  init() {
    this._super(...arguments);

    // TODO handle request error
    // TODO turn off handler after navigating away
    this.get('application.socket').on('join', data => {
      Ember.Logger.log('User joined the game', data);
      this.set(`game.${data.position}`, data.user);
    });
  }
});
