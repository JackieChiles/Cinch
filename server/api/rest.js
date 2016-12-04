const express = require('express');
const app = express();
const fakeData = require('./fake-data.js');
const mime = 'application/json';

// Returns a list of AI agents
app.get('/api/v1/agents', (req, res) => {
  res.type(mime).send({
    data: fakeData.agents
  });
});

// Returns a list of games
app.get('/api/v1/games', (req, res) => {
  res.type(mime).send({ data: [] });
});

exports.start = () => app.listen(3000, () => console.log('Started API server...'));
