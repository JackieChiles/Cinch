const IntlMessageFormat = require('intl-messageformat');

const strings = {
  'en-US': {
    system: 'System',
    userJoin: '{name} joined the game in seat {seat}',
    userLeave: '{name} left the game. Seat {seat} is now empty.',
    userBid: '{name} bid {bidValue, plural, =0 {pass} =5 {cinch} other {#}}.',
    userPlay: '{name} played {rank}{suit}'
  }
};

module.exports = {
  t(key, params, locale = 'en-US') {
    const localeStrings = strings[locale];

    if (!localeStrings || !localeStrings[key]) {
      return key;
    }

    return new IntlMessageFormat(localeStrings[key], locale).format(params);
  }
};
