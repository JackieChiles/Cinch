import Ember from 'ember';

export default Ember.Controller.extend({
  games: Ember.computed.reads('model'),

  selectGame(game) {
    this.transitionToRoute('games.join', game);
  }
});
