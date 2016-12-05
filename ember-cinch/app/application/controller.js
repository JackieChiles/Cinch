import Ember from 'ember';

export default Ember.Controller.extend({
  socketIo: Ember.inject.service(),

  connectSocket() {
    const socket = this.get('socketIo').socketFor('localhost:3000');
    socket.on('connect', () => console.log('Connected to socket server'));
  },

  init() {
    this._super(...arguments);
    this.connectSocket();
  }
});
