import DS from 'ember-data';
import ENV from 'ember-cinch/config/environment';

export default DS.RESTAdapter.extend({
  host: ENV.apiHost,
  namespace: 'api/v1'
});
