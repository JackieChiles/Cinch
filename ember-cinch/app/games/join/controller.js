import Ember from 'ember';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),
  game: Ember.computed.reads('model'),
  takeSeat(seat) {
    this.get('ajax').post('join', {
      // TODO player ID and name
      player: {},
      gameId: this.get('game.id'),
      seat
    });
  }
});
