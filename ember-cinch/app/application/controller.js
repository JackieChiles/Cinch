import Ember from 'ember';

export default Ember.Controller.extend({
  socketIo: Ember.inject.service(),
  ajax: Ember.inject.service(),

  user: null,
  socket: null,

  connectSocket() {
    const socket = this.get('socketIo').socketFor('localhost:3000');
    socket.on('connect', () => Ember.Logger.info('Connected to socket server'));
    this.set('socket', socket);
  },

  // Retrieves info for a new user from the server
  getUserInfo() {
    this.get('ajax').request('user').then(response => {
      this.set('user', response.user);
    });
  },

  init() {
    this._super(...arguments);
    this.connectSocket();
    this.getUserInfo();
  }
});
