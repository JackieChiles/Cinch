const express = require('express');
const app = express();
const fakeData = require('./fake-data.js');
const mime = 'application/json';
const gameEngine = require('../engine/game-engine.js').engine;

// Set up headers for all requests
// Allow access from localhost for development
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', 'http://localhost:4200');
  next();
});

// Returns a list of AI agents
app.get('/api/v1/agents', (req, res) => {
  res.type(mime).send({
    agents: fakeData.agents
  });
});

// Returns a list of games
app.get('/api/v1/games', (req, res) => {
  res.type(mime).send({ games: gameEngine.getGameList() });
});

// Returns a game by id
app.get('/api/v1/games/:gameId', (req, res) => {
  const game = gameEngine.getGameList().filter(game => game.id === req.params.id)[0];

  if (game) {
    res.type(mime).send(game);
  }
});

// Starts a new game
app.post('/api/v1/start', (req, res) => {
  res.type(mime).send(gameEngine.startNew(req));
});

exports.start = () => app.listen(3000);
