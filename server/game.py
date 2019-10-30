"""Game object for managing game properties, players, and game states."""
from datetime import datetime
import common
import cards as cards
from bidict import bidict
import copy
from math import ceil

# Constants and global variables
WINNING_SCORE = 11
CINCH_POINTS = 10
STARTING_HAND_SIZE = 9
NUM_TEAMS = 2
TEAM_SIZE = 2
NUM_PLAYERS = NUM_TEAMS * TEAM_SIZE
MAX_HANDS = 16 # Not part of game rules; intended to prevent AI problems.
               # Can be modified later if actual gameplay is trending longer.
BID_PASS=0
BID_CINCH=5
EVEN_TEAM = 0
ODD_TEAM = 1


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
            'active_player': None,
            'leader': None,
            'dealer': None,
            'even_team_score': 0,
            'odd_team_score': 0
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

    def is_game_over(self):
        return self.gs['even_team_score'] > WINNING_SCORE or self.gs['odd_team_score'] > WINNING_SCORE

    def is_game_started(self):
        return self.phase != 'pregame'

    def send_error(self, message, user_id):
        self.send_user_data({
            'action': 'error',
            'message': message
        }, user_id)

    def join(self, data, user_id):
        user_seat = -1

        if self.is_game_full():
            # Error if all seats are full
            self.send_error('Game is full. Could not join.', user_id)
            return
        elif 'seat' in data:
            user_seat = data['seat']

            # TODO handle invalid requested seat
            if user_seat in self.gs['seats']:
                # Error if specified seat is occupied
                self.send_error('Seat is occupied. Could not join.', user_id)
            else:
                # Join in specified seat if not occupied
                self.gs['seats'][user_seat] = user_id
        else:
            # If no specified seat, join in first available
            for seat in range(NUM_PLAYERS):
                if seat not in self.gs['seats']:
                    user_seat = seat
                    self.gs['seats'][user_seat] = user_id
                    break

        # If all seats filled, start game
        if self.is_game_full() and not self.is_game_started():
            self.start_game()
            self.broadcast_action('join', user_seat, True)

    def broadcast_action(self, action, actor, include_hands=False):
        data = {
            'action': action,
            'trick': self.gs['trick'],  # Always include trick for convenience
            'actor': actor,
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

    def get_hand_dealer(self, trick):
        actions = self.get_actions_this_trick_or_earlier(trick)

        while True:
            try:
                action = next(actions)

                if 'dealer' in action:
                    return action['dealer']
            except StopIteration:
                break

        return None

    def get_actions_this_trick_or_earlier(self, trick):
        return reversed(filter(lambda action['trick'] > trick, self.actions))

    def get_hand_bid_actions(self, trick):
        # Filter out all actions after this trick
        # Reverse actions and find the first four bid actions
        actions = self.get_actions_this_trick_or_earlier(trick)
        bid_actions = []

        while len(bid_actions) < NUM_PLAYERS:
            try:
                action = next(actions)

                if action['action'] == 'bid':
                    bid_actions.append(action)
            except StopIteration:
                break

        return bid_actions

    def get_bid_from_bid_action(self, action):
        return action['bids'][action['actor']]

    def get_hand_bid_winning_action(self, trick):
        bid_actions = self.get_hand_bid_actions(trick)
        high = 0
        winners = []
        dealer = self.get_hand_dealer(trick)
        dealer_bid_action = None

        # Build list of all seats with highest bid
        for action in bid_actions:
            if self.get_bid_from_bid_action(action) >= high:
                winners.append(action)

            if action['actor'] == dealer:
                dealer_bid_action = action

        # If only one high bid, that player wins
        if len(winners) == 1:
            return winners[0]

        # If multiple high bids, winner either got stuck or counter-cinched
        return dealer_bid_action

    def get_current_high_bid(self):
        return self.get_bid_from_bid_action(self.get_hand_bid_winning_action(self.gs['trick']))

    def get_current_bid_winner(self):
        return self.get_hand_bid_winning_action(self.gs['trick'])['actor']

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

    def get_trick_play_actions(self, trick):
        return filter(lambda action: action['action'] == 'play' and action['trick'] == trick, self.actions)

    def get_hand_trick_range(self, trick):
        return range(trick - (trick - 1) % STARTING_HAND_SIZE, trick)

    def get_trick_led_play_action(self, trick):
        return self.get_trick_play_actions(trick)[0]

    def get_card_from_play_action(self, action):
        return cards.Card(action['plays'][action['actor']])

    def get_trick_led_card(self, trick):
        return self.get_card_from_play_action(self.get_trick_led_play_action(trick))

    def get_trick_winning_play_action(self, trick):
        play_actions = self.get_trick_play_actions(trick)
        led_play_action = self.get_trick_led_play_action(trick)
        card_led = self.get_card_from_play_action(led_play_action)
        trump = self.get_trick_trump(trick)
        winning_action = led_play_action

        for action in play_actions:
            card = self.get_card_from_play_action(action)
            winning_card = self.get_card_from_play_action(winning_action)

            if card.suit == trump:
                if winning_card.suit != trump or card.rank > winning_card.rank:
                    winning_action = action
            elif card.suit == card_led.suit and card.rank > winning_card.rank:
                winning_action = action

        return winning_action

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

        self.broadcast_action('bid', user_seat)

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

        # Check for end of trick and handle.
        if self.is_trick_over():
            # Check for end of hand and handle.
            if self.is_hand_over():
                self.score_hand()

                if self.is_game_over():
                    return self.update_game_state({
                        'phase': 'postgame'
                    })

            self.update_game_state({
                'active_player': self.get_trick_winning_seat(),
                'trick': self.gs['trick'] + 1,
                'plays': {}
            })
        else:
            self.advance_player()

        self.broadcast_action('play', user_seat)

    def update_score_from_bid(self, score, bid):
        if score < bid:
            # Set: score reduced by bid points
            return -bid
        elif bid == BID_CINCH:
            if score == 0:
                # Made cinch from zero: automatic win
                return WINNING_SCORE

            # Made cinch at non-zero score: ten points
            return score + CINCH_POINTS

        # Made bid: score increased by scored points
        return score

    def score_hand(self):
        trick = self.gs['trick']

        # TODO implement these methods
        high_play_action = self.get_hand_high_play_action(trick)
        low_play_action = self.get_hand_low_play_action(trick)
        jack_play_action = self.get_hand_jack_winning_play_action(trick)
        even_team_game_points = self.get_hand_even_game_points(trick)
        odd_team_game_points = self.get_hand_odd_game_points(trick)
        even_team_score = 0
        odd_team_score = 0

        # TODO use 0 and 1 index instead of variable for each team score
        if high_play_action and high_play_action['actor'] % 2 == 0:
            even_team_score += 1
        elif high_play_action:
            odd_team_score += 1

        if low_play_action and low_play_action['actor'] % 2 == 0:
            even_team_score += 1
        elif low_play_action:
            odd_team_score += 1

        if jack_play_action and jack_play_action['actor'] % 2 == 0:
            even_team_score += 1
        elif jack_play_action:
            odd_team_score += 1

        if even_team_game_points > odd_team_game_points:
            even_team_score += 1
        elif even_team_game_points < odd_team_game_points:
            odd_team_score += 1

        winning_bid_action = self.get_hand_bid_winning_action(trick)
        winning_bid = self.get_bid_from_bid_action(winning_bid_action)
        even_team_won_bid = winning_bid_action['actor'] % 2 == 0

        if even_team_won_bid:
            even_team_score = self.update_score_from_bid(even_team_score, winning_bid)
        else:
            odd_team_score = self.update_score_from_bid(odd_team_score, winning_bid)

        # TODO determine winning team
        self.update_game_state({
            'even_team_score': self.gs['even_team_score'] + even_team_score,
            'odd_team_score': self.gs['odd_team_score'] + odd_team_score
        })

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
            'trick': 1
        })

