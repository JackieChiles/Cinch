import Ember from 'ember';

export default Ember.Controller.extend({
  ajax: Ember.inject.service(),
  application: Ember.inject.controller(),

  game: Ember.computed.reads('model'),

  takeSeat(seat) {
    this.get('ajax').post('join', {
      // TODO user ID and name
      user: this.get('application.user'),
      gameId: this.get('game.id'),
      seat
    }).then(response => {
      this.transitionToRoute('play', response.game);
      this.get('application.socket').emit('join', response.game.id);
    }); // TODO handle request error
  }
});
