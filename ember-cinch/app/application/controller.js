import { inject as service } from '@ember/service';
import Evented from '@ember/object/evented';
import Controller from '@ember/controller';
import Ember from 'ember';

export default Controller.extend(Evented, {
  socketIo: service(),
  stash: service(),

  user: null,
  socket: null,
  rememberMe: true,

  connectSocket() {
    const socket = this.get('socketIo').socketFor('localhost:3000');

    this.set('socket', socket);
    const username = this.get('rememberMe') ? this.get('stash').getValue('username') : '';
    socket.emit('initialize', username, user => {
      Ember.Logger.info('Connected to socket server');
      this.set('user', user);

      if (this.get('rememberMe')) {
        this.get('stash').stashValue('username', user.name);
      }

      this.trigger('initialized');
    });
  },

  init() {
    this._super(...arguments);
    this.connectSocket();
  }
});
