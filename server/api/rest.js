const express = require('express');
const app = express();
const fakeData = require('./fake-data.js');
const mime = 'application/json';

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
  res.type(mime).send({ games: [] });
});

exports.start = () => app.listen(3000);
