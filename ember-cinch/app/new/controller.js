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
    }); // TODO handle request error;
  }
});
