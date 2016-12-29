import Ember from 'ember';
import ENV from 'ember-cinch/config/environment';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),

  agents: Ember.computed.reads('model'),

  startGame() {
    this.get('ajax').post(`${ENV.apiHost}/api/v1/start`, {});
  }
});
