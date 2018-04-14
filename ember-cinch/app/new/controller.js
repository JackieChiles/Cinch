import { reads } from '@ember/object/computed';
import Controller, { inject as controller } from '@ember/controller';

export default Controller.extend({
  application: controller(),

  agents: reads('model'),

  startGame() {
    // TODO send agent selections
    this.get('application.socket').emit('new', {
      user: this.get('application.user')
    });
  },

  init() {
    this._super(...arguments);

    // TODO handle request error
    // TODO turn off handler after navigating away
    this.get('application.socket').on('new-success', game => this.transitionToRoute('play', game));
  }
});
