import Ember from 'ember';

export default Ember.Controller.extend({
  agents: null,

  startGame() {
  },

  init() {
    this._super(...arguments);
    this.set('agents', []);
  }
});
