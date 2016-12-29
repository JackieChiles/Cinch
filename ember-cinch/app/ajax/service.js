import Ember from 'ember';
import AjaxService from 'ember-ajax/services/ajax';
import ENV from 'ember-cinch/config/environment';

export default AjaxService.extend({
  host: ENV.apiHost,
  namespace: '/api/v1',
  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      contentType: 'application/json; charset=UTF-8',
      data: JSON.stringify(data)
    });
  }
});
