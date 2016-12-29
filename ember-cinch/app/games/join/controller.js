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
    }).then(response => {
      // Respose is game object
      this.transitionToRoute('play', response);
    }); // TODO handle request error
  }
});
