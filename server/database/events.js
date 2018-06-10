const uuid = require('uuid/v4');
const AWS = require('aws-sdk');

AWS.config.update({
  region: 'us-east-1',
  endpoint: "https://dynamodb.us-east-1.amazonaws.com"
});

module.exports = {
  publish(gameEvent) {
    if (!gameEvent || !gameEvent.type) {
      console.log('Did not publish event to dynamoDB because the event object was missing or had no "type" property');
    }

    console.log("Publishing event to dynamoDB...");

    const docClient = new AWS.DynamoDB.DocumentClient();

    docClient.put({
      TableName: 'game-events',
      Item: Object.assign({ id: uuid(), timestamp: new Date().toISOString() }, gameEvent)
    }, function (err, data) {
      if (err) {
        console.error("Unable to publish event to dynamoDB. Error JSON:", JSON.stringify(err, null, 2));
      } else {
        console.log("Published event to dynamoDB:", JSON.stringify(data, null, 2));
      }
    });
  }
};
