import Ember from 'ember';
import config from './config/environment';

const Router = Ember.Router.extend({
  location: config.locationType,
  rootURL: config.rootURL
});

Router.map(function() {
  this.route('home');
  this.route('new');
  this.route('games', function() {
    this.route('join', { path: ':gameId' });
  });
  this.route('history');
  this.route('play', { path: 'play/:gameId' });
});

export default Router;
