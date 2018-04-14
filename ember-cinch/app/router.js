import EmberRouter from '@ember/routing/router';
import config from './config/environment';

const Router = EmberRouter.extend({
  location: config.locationType,
  rootURL: config.rootURL
});

Router.map(function() {
  this.route('home', { path: '/' });
  this.route('new');
  this.route('games', function() {
    this.route('join', { path: ':gameId' });
  });
  this.route('history');
  this.route('play', { path: 'play/:gameId' });
});

export default Router;
