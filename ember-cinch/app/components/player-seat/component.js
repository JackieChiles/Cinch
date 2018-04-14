import Component from '@ember/component';

export default Component.extend({
  classNames: ['flex-35'],

  // Parameter, user object with 'id' and 'name'
  user: null,

  // Action that can be passed as a parameter. Property 'seat' will be passed as the solitary argument.
  takeSeat() {}
});
