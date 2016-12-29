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
      // Response is game object
      this.transitionToRoute('play', response);
    }); // TODO handle request error
  }
});
