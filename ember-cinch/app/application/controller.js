import Ember from 'ember';

export default Ember.Controller.extend({
  socketIo: Ember.inject.service(),
  ajax: Ember.inject.service(),

  user: null,

  connectSocket() {
    const socket = this.get('socketIo').socketFor('localhost:3000');
    socket.on('connect', () => console.log('Connected to socket server'));
  },

  // Retrieves info for a new user from the server
  getUserInfo() {
    this.get('ajax').request('user').then(user => {
      this.set('user', user);
    });
  },

  init() {
    this._super(...arguments);
    this.connectSocket();
    this.getUserInfo();
  }
});
