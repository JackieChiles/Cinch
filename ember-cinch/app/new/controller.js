import Ember from 'ember';
import ENV from 'ember-cinch/config/environment';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),

  agents: Ember.computed.reads('model'),

  startGame() {
    // TODO send agent selections
    this.get('ajax').post('start', {});
  }
});
