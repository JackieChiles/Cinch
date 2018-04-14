import { reads } from '@ember/object/computed';
import Controller from '@ember/controller';

export default Controller.extend({
  games: reads('model'),

  selectGame(game) {
    this.transitionToRoute('games.join', game);
  }
});
