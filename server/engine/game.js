const uuid = require('uuid/v4');
const shuffle = require('shuffle-array');
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
  NORTH_SOUTH: 'north-south',
  EAST_WEST: 'east-west'
};
const HAND_SIZE = 9;
const NUM_PLAYERS = 4;
const WINNING_SCORE = 11;

// Generates and shuffles a new 52-card deck
const getNewDeck = () => shuffle(suits.reduce((deck, suit) => ranks.reduce((cards, rank) => (cards.push({ rank, suit }), cards), deck), []));
                                

/*
  Game class

  initialState will evenutually contain agent selections and such
  io is socket.io instance
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

  // Position of the player currently taking a turn
  this.activePlayer = this.getNextPosition(this.dealer);

  // Trump suit (string) for the current hand
  this.trump = null;

  // Team match scores for north-south and east-west
  this.nsScore = 0;
  this.ewScore = 0;

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

  /*
    Key is trick number, value is position that took it. Must be cleared at end of hand.
    Can be determined from 'plays' but this is a convenience property so we don't have to recompute.
   */
  this.trickWinners = {};

  // Emits a socket.io event to all in this game room
  this.emitSocketEventToRoom = function (event, data) {
    io.to(this.id).emit(event, data);
  };

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
      activePlayer: this.activePlayer,
      nsScore: this.nsScore,
      ewScore: this.ewScore,
      hands: {}
    };

    console.log(`Looking for hand in game state for user ${userId}. Current hands:\n`, this.hands);

    if (userId && this.hands[userId]) {
      console.log(`Found hand in game state for user ${userId} `, this.hands[userId]);
      state.hands[userId] = this.hands[userId];
    }

    return state;
  };

  // Generates a new hand of HAND_SIZE
  this.getNewHand = function () {
    return this.deck.splice(-HAND_SIZE)
  };

  // Returns the position of the given user. Returns null if not found
  this.getUserPosition = function (userId) {
    return this.north.id === userId ? 'north' :
      this.east.id === userId ? 'east' :
      this.south.id === userId ? 'south' :
      this.west.id === userId ? 'west' :
      null;
  };

  // Given a current position, returns the next position in turn order
  this.getNextPosition = function (position) {
    return position === 'north' ? 'east' :
      position === 'east' ? 'south' :
      position === 'south' ? 'west' :
      'north';
  }

  // Advances to the next position in turn order
  this.advancePosition = function () {
    this.activePlayer = this.getNextPosition(this.activePlayer);
    return activePlayer;
  }

  // Returns 'true' if all seats are full, otherwise 'false'
  this.isFull = function () {
    return this.north && this.east && this.south && this.west;
  };

  // Join a user to an unoccupied seat
  this.join = function (seat, user) {
    if (seat && user && !this[seat]) {
      this[seat] = user;
      this.hands[user.id] = this.getNewHand();

      if (this.isFull()) {
        // All seats are filled; start the game
        this.phase = 'bid';
        this.emitSocketEventToRoom('start', {
          phase: this.phase
        });
      }

      console.log('User join successful. Hand generated\n', this.hands[user.id], '\nNew deck length ', this.deck.length);

      return this.getGameState(user.id);
    }

    console.log('User join unsuccessful');
  };

  // Returns bids for the given hand
  this.getHandBids = function (hand) {
    return this.bids.filter(bid => bid.hand === hand);
  };

  // Returns bids for the current hand
  this.getCurrentHandBids = function () {
    return getHandBids(this.hand);
  };

  // Returns the winning bid for the given hand. Returns null if no bids found for hand.
  this.getWinningBid = function (hand) {
    const handBids = getHandBids;

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

      this.emitSocketEventToRoom('bid', {
        position,
        bidValue,
        phase: this.phase,
        activePlayer: this.activePlayer
      });
    } else {
      console.warn('Illegal bid attempted ', userId, bidValue);
      // TODO handle illegal bid
    }
  };

  // Returns an array of cards that are currently in play this trick
  this.getCardsInPlay = function () {
    return this.plays.filter(play => play.hand === this.hand && play.trick === this.trick).map(play => play.card);
  };

  // Returns true if play from given user is legal at this time, otherwise false
  this.isPlayLegal = function (userId, card) {
    const userPosition = this.getUserPosition(userId);
    const cardsInPlay = this.getCardsInPlay();
    const leadCard = cardsInPlay[0];
    const hand = this.hands[userId];

     // Card must be in hand
    return hand.filter(c => c.suit === card.suit && c.rank === card.rank).length &&
      (
        // Anything legal on lead
        !leadCard ||

        // Following suit
        leadCard.suit === card.suit ||

        // Trumping
        this.trump === card.suit ||

        // Throwing off-suit; lead suit not in hand
        hand.filter(c => c.suit === leadCard.suit).length === 0
      );
  };

  this.determineCurrentTrickWinner = function () {
    // TODO implement
  };

  // TODO implement
  this.updateScores = function () {
    const playsForHand = this.plays.filter(play => play.hand === this.hand);

    if (playsForHand.length === NUM_PLAYERS * HAND_SIZE) {
      // Only update scores if all plays have been made for hand
      const trump = playsForHand[0].card.suit;

    } else {
      console.warn(`Attempted to update scores before hand '${this.hand}' was over`);
    }
  };

  this.dealHand = function () {
    this.hands = {};
    this.deck = getNewDeck();
    this.hands[north.id] = this.getNewHand();
    this.hands[south.id] = this.getNewHand();
    this.hands[east.id] = this.getNewHand();
    this.hands[west.id] = this.getNewHand();
  };

  // Applies the given play from the given user, updates state, and emits play event to room
  this.play = function (userId, card) {
    if (this.isPlayLegal(userId, card)) {
      const position = this.getUserPosition(userId);
      let trickWinner = null;

      // If game is over, will be string 'east-west' or 'north-south' indicating winning team
      let gameWinner = null;

      this.plays.push({
        position,
        hand: this.hand,
        trick: this.trick,
        card
      });

      const cardsInPlay = this.getCardsInPlay();

      if (cardsInPlay.length === NUM_PLAYERS) {
        // Trick is over
        trickWinner = this.determineCurrentTrickWinner();
        this.trickWinners[this.trick] = trickWinner;

        if (this.trick === HAND_SIZE) {
          // Hand is over
          this.updateScores();

          const isNorthSouthOver = this.nsScore >= WINNING_SCORE;
          const isEastWestOver = this.ewScore >= WINNING_SCORE;

          if (isNorthSouthOver || isEastWestOver) {
            // Game is over
            if (isNorthSouthOver && isEastWestOver) {
              // Both teams reached winning score; winner is this hand's bid winner
              const winningBid = this.getCurrentHandWinningBid();
              gameWinner = ['north', 'south'].indexOf(winningBid.position) > -1 ? teams.NORTH_SOUTH :
                teams.EAST_WEST;
            } else if (isNorthSouthOver) {
              gameWinner = teams.NORTH_SOUTH;
            } else {
              gameWinner = teams.EAST_WEST;
            }
          } else {
            // Hand is over, but game still in progress
            this.phase = 'bid';
            this.hand = this.hand + 1;
            this.trick = 1;
            this.dealer = getNextPosition(this.dealer);
            this.dealHand();
            this.activePlayer = getNextPosition(this.dealer);
          }
          
        } else {
          // Trick is over, but hand still in progress
          this.activePlayer = trickWinner;
          this.trick = this.trick + 1;
        }
      } else {
        // Trick still in progress
        this.advancePosition();
      }

      this.emitSocketEventToRoom('play', {
        position,
        card,
        trickWinner,
        gameWinner,
        phase: this.phase,
        activePlayer: this.activePlayer,
        nsScore: this.nsScore,
        ewScore: this.ewScore,
        trick: this.trick,
        hand: this.hand
      });
    } else {
      console.warn('Illegal play attempted ', userId, card);
      // TODO handle illegal play
    }
  };
};

module.exports = Game;
