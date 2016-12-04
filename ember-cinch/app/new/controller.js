import Ember from 'ember';

export default Ember.Controller.extend({
  agents: null,

  startGame() {
  },

  populateAgents() {
    this.store.findAll('agent').then(agents => {
      this.set('agents', agents);
    });
  },

  init() {
    this._super(...arguments);
    this.populateAgents();
  }
});
