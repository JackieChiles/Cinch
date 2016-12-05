const api = require('./api/rest.js');
require('./api/sockets.js').init(api.start());
console.log('Started API server...')
