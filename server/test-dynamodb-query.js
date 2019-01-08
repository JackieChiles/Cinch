const AWS = require('aws-sdk');

AWS.config.update({
  region: 'us-east-1',
  endpoint: "https://dynamodb.us-east-1.amazonaws.com"
});

const docClient = new AWS.DynamoDB.DocumentClient();

const params = {
  TableName: 'game-events',
  IndexName: 'gameId-timestamp-index',
  KeyConditionExpression: 'gameId = :gameId',
  ExpressionAttributeValues: {
    ':gameId': 'a2186a32-9426-4ddb-901d-3362b4e56354'
  }
};

docClient.query(params, function (err, data) {
  if (err) console.log(err);
  else console.log(data);
});
