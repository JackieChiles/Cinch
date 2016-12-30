import DS from 'ember-data';

export default DS.Model.extend({
  north: DS.attr(),
  east: DS.attr(),
  south: DS.attr(),
  west: DS.attr()
});
