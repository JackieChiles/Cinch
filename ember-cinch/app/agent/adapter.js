import DS from 'ember-data';
import ENV from 'ember-cinch/config/environment';

export default DS.JSONAPIAdapter.extend({
  host: ENV.host,
  namespace: 'api/v1'
});
