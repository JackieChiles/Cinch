import { reads, alias } from '@ember/object/computed';
import { inject as service } from '@ember/service';
import Controller, { inject as controller } from '@ember/controller';

export default Controller.extend({
  application: controller(),
  stash: service(),

  socket: reads('application.socket'),
  user: reads('application.user'),
  rememberMe: alias('application.rememberMe'),
  username: '',

  generateUsername() {
    this.get('socket').emit('generate-username', name => this.set('username', name));
  },

  updateUsername() {
    this.get('socket').emit('update-username', this.get('username'), name => {
      // Update the user object
      this.set('user.name', name);

      // Save locally
      if (this.get('rememberMe')) {
        this.get('stash').stashValue('username', name);
      }
    });
  },

  toggleRememberMe() {
    this.toggleProperty('rememberMe');

    if (!this.get('rememberMe')) {
      this.get('stash').clearValue('username');
    }
  },

  refreshUsernameInput() {
    this.set('username', this.get('user.name'));
  },

  init() {
    this._super(...arguments);
    this.refreshUsernameInput();
    this.get('application').on('initialized', () => this.refreshUsernameInput());
  }
});
