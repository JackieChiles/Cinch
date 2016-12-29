import Ember from 'ember';
import ENV from 'ember-cinch/config/environment';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),

  agents: Ember.computed.reads('model'),

  startGame() {
    // TODO send agent selections
    this.get('ajax').post('start', {}).then(response => {
      // Response is game object
      this.transitionToRoute('play', response);
    }); // TODO handle request error;
  }
});
