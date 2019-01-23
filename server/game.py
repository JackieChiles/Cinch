"""Game object for managing game properties, players, and game states."""
from datetime import datetime
import common
import cards as cards
from bidict import bidict
import copy

# Constants and global variables
WINNING_SCORE = 11
STARTING_HAND_SIZE = 9
NUM_TEAMS = 2
TEAM_SIZE = 2
NUM_PLAYERS = NUM_TEAMS * TEAM_SIZE
MAX_HANDS = 16 # Not part of game rules; intended to prevent AI problems.
               # Can be modified later if actual gameplay is trending longer.
BID_PASS=0
BID_CINCH=5


class Game:
    """Define object for Game object with instance variables:

        stack_deck (bool): fixed hands for testing purposes.
        deck_seed (float)[0..1]: used to seed if stack_deck is True
        id (integer): unique id for game object
        mode (integer): setting for game mode
        players (list): array of Player objects for players in game
        teams (dict): player id : local player num pairings (?)
        gs (object): current game state
        deck (object): Deck object containing Card objects

    """
    def __init__(self, send_user_data):
        self.gs = {
            'phase': 'pregame',
            'seats': bidict({}),
            'plays': bidict({}),
            'bids': {},
            'trick': 1,
            'hand': 1
        }

        self.unsent_gs_updates = {}
        self.actions = []
        self.deck = cards.Deck()
        self.send_user_data = send_user_data

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Cinch game with players: {0}".format(
            ", ".join(str(plr.name) for plr in self.players))

    def is_game_full(self):
        return len(self.gs['seats']) >= NUM_PLAYERS

    def is_bidding_over(self):
        return len(self.gs['bids']) >= NUM_PLAYERS

    def is_trick_over(self):
        return len(self.gs['plays']) >= NUM_PLAYERS

    def is_hand_over(self):
        return self.gs['trick'] == STARTING_HAND_SIZE

    def is_game_started(self):
        return self.phase != 'pregame'

    def send_error(self, message, user_id):
        self.send_user_data({
            'action': 'error',
            'message': message
        }, user_id)

    def join(self, data, user_id):
        if self.is_game_full():
            # Error if all seats are full
            self.send_error('Game is full. Could not join.', user_id)
            return
        elif 'seat' in data:
            seat = data['seat']

            # TODO handle invalid requested seat
            if seat in self.gs['seats']:
                # Error if specified seat is occupied
                self.send_error('Seat is occupied. Could not join.', user_id)
            else:
                # Join in specified seat if not occupied
                self.gs['seats'][seat] = user_id
        else:
            # If no specified seat, join in first available
            for seat in range(NUM_PLAYERS):
                if seat not in self.gs['seats']:
                    self.gs['seats'][seat] = user_id
                    break

        # If all seats filled, start game
        if self.is_game_full() and not self.is_game_started():
            self.start_game()
            self.broadcast_action('join', True)

    def broadcast_action(self, action, include_hands=False):
        data = {
            'action': action,
            **self.unsent_gs_updates
        }

        seats = self.gs['seats']

        for seat in seats:
            if include_hands:
                data['hands'] = {seat: copy.deepcopy(self.hands[seat])}

            self.send_user_data(data, seats[seat])

        # Save the action to history including all hands when necessary
        if include_hands:
            data['hands'] = copy.deepcopy(self.hands)

        self.actions.append(data)

        # Clear unsent updates
        self.unsent_gs_updates = {}

    def update_game_state(self, updates):
        for key in updates:
            self.gs[key] = updates[key]
            self.unsent_gs_updates[key] = updates[key]

    def get_current_high_bid(self):
        winner = self.get_current_bid_winner()
        return self.gs['bids'][winner]

    def get_current_bid_winner(self):
        bids = self.gs['bids']
        high = 0
        winners = []

        # Build list of all seats with highest bid
        for seat in bids:
            if bids[seat] >= high:
                winners.append(seat)

        # If only one high bid, that player wins
        if len(winners) == 1:
            return winners[0]

        # If multiple high bids, winner either got stuck or counter-cinched
        return self.gs['dealer']

    def is_bid_legal(self, seat, bid):
        """Check a proposed bid for legality against the current gs.
        Returns True if bid is legal, or False if bid is illegal.

        seat (int)
        bid (int): integer [0-5] value of bid; PASS=0, BID_CINCH=5
        """
        if self.gs['active_player'] != seat:
            return False    # Can't bid out of turn.
        if self.gs['phase'] != 'bid':
            return False    # Can't bid during play phase.
        if bid == BID_PASS:
            return True     # Always legal to pass.
        if bid < BID_PASS or bid > BID_CINCH:
            return False    # Bid outside legal range.
        if bid > self.get_current_high_bid():
            return True     # New high bid; legal.
        if (bid == BID_CINCH) and (seat == self.gs['dealer']):
            return True     # Dealer has option to counter-cinch.

        return False        # If we get here, no legal options left.

    def get_trick_led_card(self):
        return cards.Card(self.gs['plays'][self.gs['leader']])

    def get_trick_winning_seat(self):
        plays = self.gs['plays'].inv
        card_led = self.get_trick_led_card()
        trump = self.gs['trump']
        winning_card = card_led

        for play in plays:
            card = cards.Card(play)

            if card.suit == trump:
                if winning_card.suit != trump or card.rank > winning_card.rank:
                    winning_card = card
            elif card.suit == card_led.suit and card.rank > winning_card.rank:
                winning_card = card

        return plays[winning_card.code]

    def is_play_legal(self, seat, play):
        """Check a proposed play for legality against the current gs.
        Returns True if play is legal, or False if play is illegal.
        """

        # Search player's hand for card
        hand = self.hands[seat]
        has_card = False

        for card in hand:
            if card.code == play:
                has_card = True
                break

        played_card = cards.Card(play)
        led_card = self.get_trick_led_card()

        if not has_card:
            return False      # Must play a card in hand.
        if self.gs['phase'] != 'play':
            return False      # Can't play during bid phase.
        if len(self.gs['plays']) == 0:
            return True       # No restrictions on what cards can be led.
        if played_card.suit == self.gs['trump']:
            return True       # Trump is always OK
        if played_card.suit == led_card.suit:
            return True       # Not trump, but followed suit.
        for card in hand:
            if card.suit == led_card.suit:
                return False  # Could have followed suit with a different card.

        return True           # Couldn't follow suit, throwing off.

    def deal_hand(self):
        """Deal new hand to each player and set card ownership."""
        for user_id in self.gs['seats']:
            self.hands[user_id] = sorted([
                self.deck.deal_one() for x in range(STARTING_HAND_SIZE)
            ], reverse=True)

    def bid(self, data, user_id):
        """Invoke bid processing logic on incoming bid.
        """

        if 'value' not in data:
            # TODO send error?
            return

        bid = data['value']
        user_seat = self.gs['seats'].inv[user_id]

        # Check that user is active player.
        if user_seat != self.gs['active_player']:
            # TODO send error?
            return

        is_bid_legal = self.is_bid_legal(user_seat, bid)

        if is_bid_legal is False:
            # TODO send error?
            return

        bids = self.gs['bids']
        bids[user_seat] = bid
        self.update_game_state({'bids': bids})

        if self.is_bidding_over():
            # Bidding is over, start play.
            self.update_game_state({
                'active_player': self.get_current_bid_winner(),
                'phase': 'play'
            })
        else:
            # Still bid phase, advance to next bidder
            self.advance_player()

        self.broadcast_action('bid')

    def play(self, data, user_id):
        """Invoke play processing logic on incoming play.
        """

        if 'value' not in data:
            # TODO send error?
            return

        play = data['value']
        user_seat = self.gs['seats'].inv[user_id]

        # Check that user is active player.
        if user_seat != self.gs['active_player']:
            # TODO send error?
            return

        if self.is_play_legal(user_seat, play) is False:
            # TODO send error?
            return

        hand = self.hands[user_seat]

        # Remove card from player's hand and put into play.
        for card in hand:
            if card.code == play:
                hand.remove(card)
                plays = self.gs['plays']
                plays[user_seat] = play
                self.update_game_state({'plays': plays})

                if self.gs['trump'] is None:  # First card played this hand?
                    self.update_game_state({'trump': card.suit})
                break

        # Check for end of trick and handle, otherwise return.
        if self.is_trick_over():
            self.update_game_state({
                'active_player': self.get_trick_winning_seat(),
                'trick': self.gs['trick'] + 1,
                'plays': {}
            })
        else:
            self.advance_player()
            return

        # Check for end of hand and handle, otherwise return.
        if not self.is_hand_over():
            return

        # TODO finish updating play method below
        # Log hand results and check victory conditions.
        self.gs.score_hand()
        victor = False
        for score in self.gs.scores:
            if score >= WINNING_SCORE:
                victor = True
                break

        # Also, if we've reached MAX_HANDS, end the game anyway.
        # message['win'] defaults to 0.5; client/database/stats should
        # interpret a game with a win value of 0.5 as a draw.

        if self.gs.hand_number == MAX_HANDS:
            victor = True

        # This block breaks if there are more than two teams.
        if victor:
            if self.gs.scores[self.gs.declarer % TEAM_SIZE] >= WINNING_SCORE:
                self.gs.winner = self.gs.declarer % TEAM_SIZE
            elif self.gs.scores[(self.gs.declarer + 1) % TEAM_SIZE] >= WINNING_SCORE:
                self.gs.winner = (self.gs.declarer + 1) % TEAM_SIZE
            else:
                pass # Don't need to set winner if we reached on MAX_HANDS.

            return self.publish('eog', player_num, card)

        # If no victor, set up for next hand.
        gs = self.gs # Operate on local variable for speed++

        gs.team_stacks = [[] for _ in range(NUM_TEAMS)]
        gs.dealer = gs.next_player(gs.dealer)
        gs.declarer = gs.dealer
        self.deck = cards.Deck()
        self.deal_hand()
        gs.active_player = gs.next_player(gs.dealer)
        gs.high_bid = 0
        gs.phase = 'bid'
        gs.trump = None

        self.gs = gs

        return self.publish('eoh', player_num, card)

    def publish(self, status, pNum, data):
        """Translate game actions into messages for clients.

        Also write data to the appropriate game log file on the server.

        status (str): 3-char code specifying the event type.
        Legal values:
            bid: 3/hand, normal bid.
            eob: 1/hand, final bid.
            trp: 1/hand, first card played.
            crd: 26/hand, normal card play.
            eot: 8/hand, end of trick.
            eoh: 1/hand, end of hand.
            eog: 1/game, end of game.
        pNum (int): local player number
        data (int or Card): Card object being played by player for modes
            trp, crd, eot, eoh, eog; integer encoding of bid for bid and eob.

        """
        gs = self.gs # Make local copy for speed++; it's not edited in here.

        # Initialize the output. Message always contains actvP, so do it here.
        message = {'actvP': gs.active_player}
        message['actor'] = pNum

        if status in ['sog', 'eob', 'eoh']:
            # Handle switching game modes first.
            message['mode'] = gs.phase

        if status in ['trp', 'crd', 'eot', 'eoh', 'eog']:

            if status == 'trp':
                message['trp'] = gs.trump
                # Player declared Suit as trump.

            message['playC'] = data.code
            # Player played Card.

            if status in ['eot', 'eoh', 'eog']:
                message['remP'] = gs._t_w_card.owner
                # Player won the trick with Card.

                if status in ['eoh', 'eog']:
                    message['mp'] = ['',]*NUM_TEAMS # Initialize
                    # We will end up with a list of NUM_TEAMS strings,
                    # where the string is the match points out of 'hljg' won.
                    message['mp'][gs._results['high_holder']] += 'h'
                    message['mp'][gs._results['low_holder']] += 'l'
                    try:
                        message['mp'][gs._results['jack_holder']] += 'j'
                    except TypeError: # No jack out, NoneType.
                        pass
                    try:
                        message['mp'][gs._results['game_holder']] += 'g'
                    except TypeError: # Game tied and not awarded, NoneType.
                        pass
                    message['gp'] = gs._results['game_points']
                    message['sco'] = gs.scores

                    if status == 'eog':
                        message['win'] = gs.winner

                    else: # Status must be 'eoh': Set up for next hand.
                        message['dlr'] = gs.dealer
                        # Player deals.
                        output = [message.copy() for _ in range(NUM_PLAYERS)]
                        for player in self.players:
                            output[player.pNum]['addC'] = [card.code for card
                                                           in player.hand]
                            output[player.pNum]['tgt'] = player.pNum

        elif status in ['bid', 'eob']:
            message['bid'] = data

        # Start of game is the same as end of hand except there are different
        # logging requirements, so there's a little bit of duplicated code.
        # Update: Text logging has been deprecated; this duplicated code
        # could be cleaned up or merged later, but it isn't hurting anything
        # for now.
        elif status == 'sog':
            message['dlr'] = gs.dealer
            # Player deals.
            output = [message.copy() for _ in range(NUM_PLAYERS)]
            for player in self.players:
                output[player.pNum]['addC'] = [card.code for card
                                               in player.hand]
                output[player.pNum]['tgt'] = player.pNum

        # Note: New hands are handled differently from all others because they
        # are the only ones dealing with private information. If status is
        # 'eoh'/'sog', output will be a length-4 list containing 4 dicts with
        # 'tgt' containing an integer, and 'addC' containing the new hands. If
        # not, output will be a dict with 'tgt' containing a length-4 list.
        # (With 4 meaning NUM_PLAYERS, of course.)
        if status not in ['eoh', 'sog']:
            message['tgt'] = [i for i in range(NUM_PLAYERS)]
            output = message

        if status in ['eoh', 'sog']:
            for x in output:  # output is a list
                self.gs.events.append({'hand_num':self.gs.hand_number,
                                       'timestamp':datetime.utcnow().isoformat(),
                                       'output':str(x)})
        else:
            self.gs.events.append({'hand_num':self.gs.hand_number,
                                   'timestamp':datetime.utcnow().isoformat(),
                                   'output':str(output)})

        if status in ['eoh', 'eog']:
            gs.hand_number += 1

        # if status in ['eog']:
            # self.dbupdate()

        return output

    def get_next_player(self, seat):
        """Return the seat number to the left of given seat."""
        return (seat + 1) % NUM_PLAYERS

    def advance_player(self):
        self.update_game_state({
            'active_player': self.get_next_player(self.gs['active_player'])
        })

    def start_game(self):
        """Start a new game and deal first hands.
        """

        self.deal_hand()

        dealer = 0

        self.update_game_state({
            'dealer': dealer,
            'active_player': self.get_next_player(dealer),
            'phase': 'bid',
            'trick': 1,
            'hand': 1
        })

    def join_game_in_progress(self, pNum, name):
        """Facilitate a player joining a game in progress.

        pNum (int): The target player number.
        name (str): The player's nickname.
        """
        self.players[pNum].name = name

        message = dict(
            actvP=self.gs.active_player,
            actor=None,
            addC=[card.code for card in self.players[pNum].hand],
            dlr=self.gs.dealer,
            mode=self.gs.phase,
            tgt=pNum,
            resumeData=dict(
                handSizes=[len(x.hand) for x in self.players],
                trp=self.gs.trump,
                sco=self.gs.scores,
                highBid=self.gs.high_bid,
                declarer=self.gs.declarer,
                cip=[(c.code, c.owner) for c in self.gs.cards_in_play])
            )
        return message
