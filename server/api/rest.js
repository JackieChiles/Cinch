const express = require('express');
const app = express();
const fakeData = require('./fake-data.js');

// Returns a list of AI agents
app.get('/api/v1/agents', (req, res) => {
  res.type('application/json').send(fakeData.agents);
});

// Returns a list of games
app.get('/api/v1/games', (req, res) => {
  res.type('application/json').send([]);
});

exports.start = () => app.listen(3000, () => console.log('Started API server...'));
