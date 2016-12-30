import Ember from 'ember';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),
  application: Ember.inject.controller(),

  agents: Ember.computed.reads('model'),

  startGame() {
    // TODO send agent selections
    this.get('ajax').post('start', {
      user: this.get('application.user')
    }).then(response => {
      this.transitionToRoute('play', response.game);
      this.get('application.socket').emit('join', response.game.id);
    }); // TODO handle request error;
  }
});
