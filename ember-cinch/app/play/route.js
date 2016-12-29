import Ember from 'ember';

export default Ember.Route.extend({
  store: Ember.inject.service(),

  model(params) {
    return this.get('store').findRecord('game', params.gameId);
  },

  serialize(model) {
    return { gameId: model.id };
  }
});
