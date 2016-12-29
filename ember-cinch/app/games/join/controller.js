import Ember from 'ember';

export default Ember.Controller.extend({
  game: Ember.computed.reads('model')
});
