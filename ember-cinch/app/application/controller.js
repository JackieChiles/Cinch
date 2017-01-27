import Ember from 'ember';

export default Ember.Controller.extend({
  socketIo: Ember.inject.service(),
  ajax: Ember.inject.service(),

  user: null,
  socket: null,

  connectSocket() {
    const socket = this.get('socketIo').socketFor('localhost:3000');
    socket.on('connection-success', user => {
      Ember.Logger.info('Connected to socket server');
      this.set('user', user);
    });
    this.set('socket', socket);
  },

  init() {
    this._super(...arguments);
    this.connectSocket();
  }
});
