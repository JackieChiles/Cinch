import Ember from 'ember';

export default Ember.Controller.extend({
  newGame() {
    this.transitionToRoute('new');
  },
  joinGame() {
  },
  viewPastGames() {
  }
});
