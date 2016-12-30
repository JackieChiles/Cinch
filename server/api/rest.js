const express = require('express');
const app = express();
const fakeData = require('./fake-data');
const mime = 'application/json';
const gameEngine = require('../engine/game-engine');
const userManager = require('../users/user-manager');
const bodyParser = require('body-parser');

// Set up headers for all requests
// Allow access from localhost for development
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:4200');
  res.header('Access-Control-Allow-Headers', 'origin, content-type, accept');
  next();
});

// Set up parsing of POST request data
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Returns a new user object
app.get('/api/v1/user', (req, res) => {
  res.type(mime).send({
    user: userManager.getNewUser()
  });
});

// Returns a list of AI agents
app.get('/api/v1/agents', (req, res) => {
  res.type(mime).send({
    agents: fakeData.agents
  });
});

// Returns a list of games
app.get('/api/v1/games', (req, res) => {
  console.log('Retrieved game list');
  res.type(mime).send({ games: gameEngine.getGameList() });
});

// Returns a game by id
// TODO move logic to engine
// TODO handle no matching game found
app.get('/api/v1/games/:gameId', (req, res) => {
  const game = gameEngine.getGameList().filter(game => game.id === req.params.gameId)[0];

  if (game) {
    console.log(`Retrieved game '${game.id}'`);
    res.type(mime).send({
      game
    });
  }
});

// Starts a new game
app.post('/api/v1/start', (req, res) => {
  res.type(mime).send({
    game: gameEngine.startNew(req.body)
  });
});

// Joins an active game
app.post('/api/v1/join', (req, res) => {
  const game = gameEngine.join(req.body);
  console.log('Sending response to join request\n', game);
  res.type(mime).send({
    game
  });
});

exports.start = () => app.listen(3000);
