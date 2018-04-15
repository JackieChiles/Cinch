import { inject as service } from '@ember/service';
import Route from '@ember/routing/route';

export default Route.extend({
  store: service(),

  model(params) {
    return this.get('store').findRecord('game', params.gameId);
  },

  afterModel(model) {
    this.controllerFor('play').set('messages', (model && model.messages) || []);
  },

  serialize(model) {
    return { gameId: model.id };
  },

  actions: {
    didTransition() {
      this.controller.setup();
      return true;
    },

    willTransition() {
      this.controller.teardown();
    }
  }
});
