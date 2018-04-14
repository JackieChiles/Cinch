import { inject as service } from '@ember/service';
import Route from '@ember/routing/route';

export default Route.extend({
  store: service(),

  model(params) {
    return this.get('store').findRecord('game', params.gameId);
  },

  serialize(model) {
    return { gameId: model.id };
  }
});
