import Ember from 'ember';

export default Ember.Controller.extend({
  application: Ember.inject.controller(),

  user: Ember.computed.reads('application.user'),
  game: Ember.computed.reads('model')
});
