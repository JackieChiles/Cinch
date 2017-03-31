import DS from 'ember-data';

export default DS.Model.extend({
  north: DS.attr(),
  east: DS.attr(),
  south: DS.attr(),
  west: DS.attr(),
  phase: DS.attr(),
  trick: DS.attr(),
  hand: DS.attr(),
  dealer: DS.attr(),
  activePlayer: DS.attr(),
  nsScore: DS.attr(),
  ewScore: DS.attr(),
  hands: DS.attr(),
  currentBids: DS.attr(),
  currentPlays: DS.attr()
});
