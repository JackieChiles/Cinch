import Ember from 'ember';

export default Ember.Controller.extend(Ember.Evented, {
  socketIo: Ember.inject.service(),
  stash: Ember.inject.service(),

  user: null,
  socket: null,

  connectSocket() {
    const socket = this.get('socketIo').socketFor('localhost:3000');

    socket.on('connection-success', user => {
      Ember.Logger.info('Connected to socket server');
      this.set('user', user);
      this.get('stash').stashValue('username', user.name);
      this.trigger('connection-success');
    });

    this.set('socket', socket);
    socket.emit('initialize', this.get('stash').getValue('username'));
  },

  init() {
    this._super(...arguments);
    this.connectSocket();
  }
});
