import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller(),

  user: Ember.computed.reads('application.user'),
  username: '',
  rememberMe: true,

  init() {
    this._super(...arguments);

    this.get('application').on('connection-success', () => {
      this.set('username', this.get('user.name'));
    });
  }
});
