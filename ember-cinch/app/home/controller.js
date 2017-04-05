import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller(),
  stash: Ember.inject.service(),

  socket: Ember.computed.reads('application.socket'),
  user: Ember.computed.reads('application.user'),
  rememberMe: Ember.computed.alias('application.rememberMe'),
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
