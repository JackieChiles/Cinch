import Component from '@ember/component';

export default Component.extend({
  classNames: ['team-score'],

  // Parameter, required, game object
  game: null,

  // Parameter, required, team score
  score: 0,

  // Parameter, required, player position string
  firstPosition: null,

  // Parameter, required, player position string
  secondPosition: null
});
