import { reads } from '@ember/object/computed';
import Controller, { inject as controller } from '@ember/controller';
import Ember from 'ember';

const PHASE_CHANGE_DELAY = 3000;

export default Controller.extend({
  application: controller(),

  user: reads('application.user'),
  game: reads('model'),

  // Messages for the game in reverse so newest message is on top
  messagesRecentFirst: Ember.computed('messages.[]', function () {
    return (this.get('messages') || []).concat([]).reverse();
  }),

  // Update the game state
  updateGame(game) {
    Ember.Logger.log('Updating game state');

    //TODO figure out phase delay
    /*
    // Update all except phase; leave a delay so final bids/plays can be shown
    const newPhase = game.phase;
    const oldGame = this.get('game');
    if (newPhase !== oldGame.phase) {
      game.phase = oldGame.phase;

      // TODO store timer variable
      Ember.run.later(() => this.set('game.phase', newPhase), PHASE_CHANGE_DELAY);
    }
    */

    this.set('game', game);
  },

  setup() {
    const socket = this.get('application.socket');

    // TODO handle request errors
    socket.on('join', data => {
      Ember.Logger.log('User joined the game');
      this.updateGame(data.game);
    });

    socket.on('leave', data => {
      Ember.Logger.log('User left the game');
      this.updateGame(data.game);
    });

    socket.on('bid', data => this.updateGame(data.game));
    socket.on('play', data => this.updateGame(data.game));
    socket.on('message', message => this.get('messages').pushObject(message));
  },

  teardown() {
    const socket = this.get('application.socket');
    socket.off('join');
    socket.off('leave');
    socket.off('bid');
    socket.off('play');
    socket.off('message');
  },

  bid(value) {
    Ember.Logger.log('Bid made', value);
    this.get('application.socket').emit('bid', {
      gameId: this.get('game.id'),
      value
    });
  },

  play(card) {
    Ember.Logger.log('Play made', card);
    this.get('application.socket').emit('play', {
      gameId: this.get('game.id'),
      card
    });
  }
});
