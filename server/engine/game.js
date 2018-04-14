const uuid = require('uuid/v4');
const shuffle = require('shuffle-array');

const gamePointValues = {
  'T': 10,
  'J': 1,
  'Q': 2,
  'K': 3,
  'A': 4
};
const ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
const suits = ['C', 'D', 'H', 'S'];
const bidOptions = {
  PASS: 0,
  ONE: 1,
  TWO: 2,
  THREE: 3,
  FOUR: 4,
  CINCH: 5
};
const teams = {
  NORTH_SOUTH: 'north_south',
  EAST_WEST: 'east_west'
};
const HAND_SIZE = 9;
const NUM_PLAYERS = 4;
const WINNING_SCORE = 11;

const isGreaterRank = (left, right) => {
  return ranks.indexOf(left) > ranks.indexOf(right);
};

const sortHand = hand => {
  return hand.sort((a, b) => {
    if (a.suit === b.suit) {
      // Suits match, compare rank
      return ranks.indexOf(a.rank) - ranks.indexOf(b.rank);
    } else {
      // Suits differ
      return a.suit < b.suit ? -1 : 1;
    }
  });
};

// Generates and shuffles a new 52-card deck
const getNewDeck = () => shuffle(suits.reduce((deck, suit) => ranks.reduce((cards, rank) => (cards.push({ rank, suit }), cards), deck), []));

/*
  Game class

  initialState will eventually contain agent selections and such
  io is api/sockets.js instance
*/
function Game(initialState, io) {
  this.id = uuid();

  // User objects for each position
  this.north = initialState ? initialState.north : null;
  this.east = initialState ? initialState.east : null;
  this.south = initialState ? initialState.south : null;
  this.west = initialState ? initialState.west : null;

  // Can be 'pregame' (before game has begun), 'bid', 'play', or 'postgame' (after game has ended)
  this.phase = 'pregame';

  // Current trick number
  this.trick = 1;

  // Current hand number
  this.hand = 1;

  // Position that last dealt
  this.dealer = 'south';

  // Given a current position, returns the next position in turn order
  this.getNextPosition = function (position) {
    return position === 'north' ? 'east' :
      position === 'east' ? 'south' :
      position === 'south' ? 'west' :
      'north';
  };

  // Position of the player currently taking a turn
  this.activePlayer = this.getNextPosition(this.dealer);

  // Trump suit (string) for the current hand
  this.trump = null;

  // Team match scores for north_south and east_west
  this.scores = {
    north_south: 0,
    east_west: 0
  };

  // If game is over, will be string 'east_west' or 'north_south' indicating winning team
  this.gameWinner = null;

  // Array of cards in deck in their current order
  this.deck = getNewDeck();

  // Key is user ID, value is array of cards
  this.hands = {};

  /*
    Ordered list of all bids made in the game in the form:
      {
        position,
        hand,
        value
      }
  */
  this.bids = [];

  /*
    Ordered list of all plays made in the game in the form:
      {
        position,
        hand,
        trick,
        card: { rank, suit }
      }
   */
  this.plays = [];

  // Returns public game state for this game
  // If user ID is passed that matches one in-game, that user's hand will be included as well
  this.getGameState = function (userId) {
    const state = {
      id: this.id,
      north: this.north,
      east: this.east,
      south: this.south,
      west: this.west,
      phase: this.phase,
      trick: this.trick,
      hand: this.hand,
      dealer: this.dealer,
      trump: this.trump,
      activePlayer: this.activePlayer,
      nsScore: this.scores[teams.NORTH_SOUTH],
      ewScore: this.scores[teams.EAST_WEST],
      gameWinner: this.gameWinner,
      hands: {},
      currentBids: this.getCurrentHandBids(),
      currentHandWinningBid: this.getCurrentHandWinningBid(),
      currentPlays: this.getCurrentTrickPlays()
    };

    if (userId && this.hands[userId]) {
      state.hands[userId] = sortHand(this.hands[userId]);
    }

    return state;
  };

  // Deals a hand of HAND_SIZE
  this.getNewHand = function () {
    return this.deck.splice(-HAND_SIZE)
  };

  // Returns the position of the given user. Returns null if not found
  this.getUserPosition = function (userId) {
    return this.north && this.north.id === userId ? 'north' :
      this.east && this.east.id === userId ? 'east' :
      this.south && this.south.id === userId ? 'south' :
      this.west && this.west.id === userId ? 'west' :
      null;
  };

  // Advances to the next position in turn order
  this.advancePosition = function () {
    this.activePlayer = this.getNextPosition(this.activePlayer);
    return this.activePlayer;
  }

  // Calls the given function for the user in each position (north, east, south, west)
  this.forEachPosition = function (operation) {
    [this.north, this.east, this.south, this.west].forEach(operation);
  };

  // Returns 'true' if all seats are full, otherwise 'false'
  this.isFull = function () {
    return this.north && this.east && this.south && this.west;
  };

  // Join a user to an unoccupied seat
  this.join = function (seat, user) {
    if (seat && user && !this[seat]) {
      this[seat] = user;
      console.log('User join successful');

      if (this.isFull()) {
        // All seats are filled; start the game
        this.dealHand();
        const phase = this.phase = 'bid';
      }

      this.forEachPosition(recipient => {
        if (recipient) {
          io.join(recipient.id, { game: this.getGameState(recipient.id) })
        }
      });

      return this.getGameState(user.id);
    }

    console.log('User join unsuccessful');
  };

  // User leaves game; returns true if all users have left
  this.leave = function (userId) {
    const position = this.getUserPosition(userId);

    if (position) {
      this[position] = null;
    }

    // TODO notify other players of departure

    return !(this.north || this.east || this.south || this.west);
  };

  // Returns bids for the given hand
  this.getHandBids = function (hand) {
    return this.bids.filter(bid => bid.hand === hand);
  };

  // Returns bids for the current hand
  this.getCurrentHandBids = function () {
    return this.getHandBids(this.hand);
  };

  // Returns the winning bid for the given hand. Returns null if no bids found for hand.
  this.getWinningBid = function (hand) {
    const handBids = this.getHandBids(hand);

    if (handBids.length) {
      // When there is a tie for high bid (either PASS or CINCH), the dealer will be one of the winning bidders and is considered the bid winner in either case. The bids array is ordered, so the dealer should be last and returned correctly by this reduce.
      return handBids.reduce((winner, bid) => bid.value >= winner.value ? bid : winner, handBids[0]);
    }

    return null;
  };

  // Returns the winning bid the the current hand
  this.getCurrentHandWinningBid = function () {
    return this.getWinningBid(this.hand);
  };

  // Returns true if bid from given user is legal at this time, otherwise false
  this.isBidLegal = function (userId, bidValue) {
    const userPosition = this.getUserPosition(userId);
    const currentWinningBid = this.getCurrentHandWinningBid();

    return this.phase === 'bid' &&            // It's time to bid
      userPosition &&                         // User is in game
      this.activePlayer === userPosition &&   // It's user's turn to bid
      (
        bidValue === bidOptions.PASS ||       // Passing is always an option
        !currentWinningBid ||                 // Any value allowed on first bid
        bidValue > currentWinningBid.value || // This bid beats previous bids

        // This is dealer's bid and they are either passing when all others have passed
        // or Cinching after someone else Cinched
        (
          bidValue === currentWinningBid.value &&
          userPosition === this.dealer &&
            (bidValue === bidOptions.PASS || bidValue === bidOptions.CINCH)
        )
      );
  };

  // Applies the given bid from the given user, updates state, and emits bid event to room
  this.bid = function (userId, bidValue) {
    if (this.isBidLegal(userId, bidValue)) {
      const position = this.getUserPosition(userId);

      this.bids.push({
        position,
        hand: this.hand,
        value: bidValue
      });

      if (this.getCurrentHandBids().length === NUM_PLAYERS) {
        // Bidding for the hand is over
        this.trick = 1;
        this.phase = 'play';
        this.activePlayer = this.getCurrentHandWinningBid().position;
      } else {
        this.advancePosition();
      }

      console.log('Bid made', userId, bidValue);

      this.forEachPosition(user => io.bid(user.id, {
        position,
        bidValue,
        game: this.getGameState(user.id)
      }));
    } else {
      console.warn('Illegal bid attempted ', userId, bidValue);
      // TODO handle illegal bid
    }
  };

  // Returns array of plays made during the given hand and trick
  this.getTrickPlays = function (hand, trick) {
    return this.plays.filter(play => play.hand === hand && play.trick === trick);
  };

  // Returns array of plays made this trick
  this.getCurrentTrickPlays = function () {
    return this.getTrickPlays(this.hand, this.trick);
  };

  // Returns an array of cards that are currently in play this trick
  this.getCardsInPlay = function () {
    return this.getCurrentTrickPlays().map(play => play.card);
  };

  // Returns true if play from given user is legal at this time, otherwise false
  this.isPlayLegal = function (userId, card) {
    const userPosition = this.getUserPosition(userId);
    const cardsInPlay = this.getCardsInPlay();
    const leadCard = cardsInPlay[0];
    const hand = this.hands[userId];

    console.log();
    console.log('isPlayLegal', this);
    console.log();

    return this.phase === 'play' &&         // It's time to play
      userPosition &&                       // User is in game
      this.activePlayer === userPosition && // It's user's turn to play

      // Card must be in hand
      hand.filter(c => c.suit === card.suit && c.rank === card.rank).length &&
      (
        !leadCard ||                                       // Anything legal on lead
        leadCard.suit === card.suit ||                     // Following suit
        this.trump === card.suit ||                        // Trumping
        !hand.filter(c => c.suit === leadCard.suit).length // Can't follow suit
      );
  };

  // Returns the play that won the specified trick
  this.getTrickWinner = function (hand, trick) {
    return this.getTrickPlays(hand, trick).reduce((previous, current) => {
      // Current card is trump which beats prior non-trump or lower trump
      if (current.card.suit === this.trump) {
        return previous.card.suit === this.trump && isGreaterRank(previous.card.rank, current.card.rank) ? previous : current;
      }

      // Current card is not trump which only beats prior lower non-trump when following suit
      return current.card.suit === previous.card.suit && isGreaterRank(current.card.rank, previous.card.rank) ? current : previous;
    });
  };

  // Returns the play that won the current trick. Does not check for legality of plays.
  this.getCurrentTrickWinner = function () {
    return this.getTrickWinner(this.hand, this.trick);
  };

  // Updates score for team given team name string and score for the hand from 0-4
  this.updateTeamScore = function (team, handScore) {    
    // Check if bidder made it or gets set
    const winningBid = this.getCurrentHandWinningBid();

    if (team.includes(winningBid.position)) {
      if (winningBid.value === bidOptions.CINCH) {
        if (handScore === 4 && this.scores[team] === 0) {
          // Team's score is zero and they made cinch: 11 points
          this.scores[team] += 11;
        } else if (handScore === 4) {
          // Team's score is anything but zero and they made cinch: 10 points
          this.scores[team] += 10;
        } else {
          // Set on a cinch bid: -10 points
          this.scores[team] -= 10;
        }
      } else if (handScore < winningBid.value) {
        // Set on a non-cinch bid
        this.scores[team] -= winningBid.value;
      } else {
        // Made it on a non-cinch bid
        this.scores[team] += handScore;
      }
    } else {
      // Team that lost the bid can't get set or cinch
      this.scores[team] += handScore;
    }
  };

  // Updates scores for each team at end of hand
  this.updateScores = function () {
    let nsHandScore = 0;
    let ewHandScore = 0;
    let nsGamePoints = 0;
    let ewGamePoints = 0;
    let highPlay;
    let lowPlay;
    let jackTakingPlay;
    const trump = this.trump;

    console.log(`Updating scores. They were previously north_south ${this.scores[teams.NORTH_SOUTH]} east_west ${this.scores[teams.EAST_WEST]}`);

    // Evaluate the plays for each trick of the hand
    for (let trick = 1; trick <= HAND_SIZE; trick++) {
      const plays = this.getTrickPlays(this.hand, trick);
      const trickWinningPlay = this.getTrickWinner(this.hand, trick);

      plays.forEach(play => {
        if (play.card.suit === trump && (!highPlay || play.card.rank > highPlay.card.rank)) {
          highPlay = play;
        }

        if (play.card.suit === trump && (!lowPlay || play.card.rank < lowPlay.card.rank)) {
          lowPlay = play;
        }

        if (play.card.suit === trump && play.card.rank === 'J') {
          jackTakingPlay = trickWinningPlay;
        }

        const gamePointValue = gamePointValues[play.card.rank];

        if (gamePointValue) {
          if (teams.NORTH_SOUTH.includes(trickWinningPlay.position)) {
            nsGamePoints += gamePointValue;
          } else {
            ewGamePoints += gamePointValue;
          }
        }
      });
    }

    // TODO throw exception if high play not set?
    // Score point for playing highest trump
    if (highPlay) {
      if (teams.NORTH_SOUTH.includes(highPlay.position)) {
        nsHandScore += 1;
      } else {
        ewHandScore += 1;
      }
    }

    // TODO throw exception if low play not set?
    // Score point for playing lowest trump
    if (lowPlay) {
      if (teams.NORTH_SOUTH.includes(lowPlay.position)) {
        nsHandScore += 1;
      } else {
        ewHandScore += 1;
      }
    }

    // Score point for taking jack of trump; might be none if jack not dealt
    if (jackTakingPlay) {
      if (teams.NORTH_SOUTH.includes(jackTakingPlay.position)) {
        nsHandScore += 1;
      } else {
        ewHandScore += 1;
      }
    }

    // Score point for most game points; might be none if tied
    if (nsGamePoints > ewGamePoints) {
      nsHandScore += 1;
    } else if (nsGamePoints < ewGamePoints) {
      ewHandScore += 1;
    }

    this.updateTeamScore(teams.NORTH_SOUTH, nsHandScore);
    this.updateTeamScore(teams.EAST_WEST, ewHandScore);

    console.log(`New scores are north_south ${this.scores[teams.NORTH_SOUTH]} east_west ${this.scores[teams.EAST_WEST]}`);
  };

  this.dealHand = function () {
    this.hands = {};
    this.deck = getNewDeck();
    this.forEachPosition(user => this.hands[user.id] = this.getNewHand());
  };

  // Applies the given play from the given user, updates state, and emits play event to room
  this.play = function (userId, card) {
    console.log('Play attempted', userId, card);
    if (this.isPlayLegal(userId, card)) {
      const position = this.getUserPosition(userId);
      let trickWinner = null;

      // Remove card from hand
      this.hands[userId] = this.hands[userId].filter(c => !(c.suit === card.suit && c.rank === card.rank));

      this.plays.push({
        position,
        hand: this.hand,
        trick: this.trick,
        card
      });

      const cardsInPlay = this.getCardsInPlay();

      if (cardsInPlay.length === NUM_PLAYERS) {
        // Trick is over
        trickWinner = this.getCurrentTrickWinner();
        console.log(`Trick ${this.trick} is over`, trickWinner);

        if (this.trick === HAND_SIZE) {
          console.log(`Hand ${this.hand} is over`);
          // Hand is over
          this.updateScores();

          const isNorthSouthOver = this.scores[teams.NORTH_SOUTH] >= WINNING_SCORE;
          const isEastWestOver = this.scores[teams.EAST_WEST] >= WINNING_SCORE;

          if (isNorthSouthOver || isEastWestOver) {
            // Game is over
            console.log('Game is over');
            this.phase = 'postgame';

            if (isNorthSouthOver && isEastWestOver) {
              // Both teams reached winning score; winner is this hand's bid winner
              const winningBid = this.getCurrentHandWinningBid();
              this.gameWinner = ['north', 'south'].indexOf(winningBid.position) > -1 ? teams.NORTH_SOUTH :
                teams.EAST_WEST;
            } else if (isNorthSouthOver) {
              this.gameWinner = teams.NORTH_SOUTH;
            } else {
              this.gameWinner = teams.EAST_WEST;
            }
          } else {
            // Hand is over, but game still in progress
            this.phase = 'bid';
            this.hand = this.hand + 1;
            this.trick = 1;
            this.dealer = this.getNextPosition(this.dealer);
            this.dealHand();
            this.activePlayer = this.getNextPosition(this.dealer);
          }
        } else {
          // Trick is over, but hand still in progress
          this.activePlayer = trickWinner.position;
          this.trick = this.trick + 1;
        }
      } else {
        // Trick still in progress
        if (cardsInPlay.length === 1 && this.trick === 1) {
          // Set trump from first play in first trick
          this.trump = card.suit;
        }

        this.advancePosition();
      }

      this.forEachPosition(user => io.play(user.id, {
        position,
        card,
        trickWinner,
        game: this.getGameState(user.id)
      }));
    } else {
      console.warn('Illegal play attempted ', userId, card);
      // TODO handle illegal play
    }
  };
};

module.exports = Game;
