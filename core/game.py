#!/usr/bin/python2
"""Game object for managing game properties, players, and game states."""
import string
import random
from datetime import datetime

import logging
log = logging.getLogger(__name__)

import common
from common import db
from core.player import Player
import core.cards as cards
from core.gamestate import GameState
import db.stats as stats


# Constants and global variables
WINNING_SCORE = 11
STARTING_HAND_SIZE = 9
NUM_TEAMS = 2
TEAM_SIZE = 2
NUM_PLAYERS = NUM_TEAMS * TEAM_SIZE
GAME_MODE = common.enum(PLAY=1, BID=2)
MAX_HANDS = 16 # Not part of game rules; intended to prevent AI problems.
               # Can be modified later if actual gameplay is trending longer.

# Bid constants
BID = common.enum(PASS=0, CINCH=5)


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
    def __init__(self):
        self.players = []
        self.gs = None
        self.deck = cards.Deck()

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Cinch game with players: {0}".format(
            ", ".join(str(plr.name) for plr in self.players))

    def check_bid_legality(self, player, bid):
        """Check a proposed bid for legality against the current gs.

        Assumes that player is indeed the active player. Returns a string
        indicating the bid type, or False if illegal bid.

        player (Player): player object of player making bid (replace w/ pNum?)
        bid (int): integer [0-5] value of bid; BID.PASS=0, BID.CINCH=5

        """
        if self.gs.game_mode != GAME_MODE.BID:
            return False    # Can't bid during play phase.
        if bid == BID.PASS:
            return 'pass'   # Always legal to pass.
        if bid < BID.PASS:
            return False    # Bid outside legal range.
        if bid > BID.CINCH:
            return False    # Bid outside legal range.
        if bid > self.gs.high_bid:
            return 'high'   # New high bid; legal.
        if (bid == BID.CINCH) & (player.pNum == self.gs.dealer):
            return 'cntr'   # Dealer has option to counter-cinch.

        return False        # If we get here, no legal options left.

    def check_play_legality(self, player, card_num):
        """Check a proposed play for legality against the current gs.

        Assumes that player is indeed the active player. Returns boolean.

        player (Player): player object of player playing a play
        card_num (int): encoding of card to be played by player

        """
        # Search player's hand for card where card_num = card.code
        has_card = False
        for card in player.hand:
            if card.code == card_num:
                has_card = True
                break

        if not has_card:
            return False     # Must play a card in hand.
        if self.gs.game_mode != GAME_MODE.PLAY:
            return False     # Can't play during bid phase.
        if len(self.gs.cards_in_play) == 0:
            return True      # No restrictions on what cards can be led.
        if card.suit == self.gs.trump:
            return True      # Trump is always OK
        if card.suit == self.gs.cards_in_play[0].suit:
            return True      # Not trump, but followed suit.
        for each_card in player.hand:
            if each_card.suit == self.gs.cards_in_play[0].suit:
                return False # Could have followed suit with a different card.

        return True          # Couldn't follow suit, throwing off.

    def dbupdate(self):
        """Write a completed gamestate to the sqlite database."""
        log.debug("Trying to add a row for the new game.")

        # Get the automatic game ID to use in the Events table in place of the
        # random engine-generated game ID. The game timestamp is that of the
        # first game event.
        autogen_game_id = db.Games.insert(
            Timestamp=self.gs.events[0]['timestamp'],
            PlayerName0=self.players[0].name,
            PlayerName1=self.players[1].name,
            PlayerName2=self.players[2].name,
            PlayerName3=self.players[3].name
        )
        log.debug("Grabbed a game_id from the database.")

        # Write everything from Events to the database.
        log.info("Writing game data for local game %s, db game %s.",
                  self.gs.game_id, autogen_game_id)

        for action in self.gs.events:
            db.Events.insert(
                game_id=autogen_game_id,
                HandNumber=action['hand_num'],
                Timestamp=action['timestamp'],
                EventString=action['output']
            )

        db.commit()

    def deal_hand(self):
        """Deal new hand to each player and set card ownership."""
        for player in self.players:
            player.hand = sorted([self.deck.deal_one() for x in range
                          (STARTING_HAND_SIZE)], reverse = True)

            for card in player.hand:
                card.owner = player.pNum

    def generate_id(self, size=6):
        """Generate random character string of specified size.

        Uses digits, upper- and lower-case letters.

        """
        chars = string.ascii_letters + string.digits
        # There is a 1.38e-07% chance of identical game_ids with 3 games.
        # This chance rises to 1% when there are 6,599 simultaneous games.
        # While not a perfect solution, we like to live dangerously.
        return ''.join(random.choice(chars) for x in range(size))

    def handle_bid(self, player_num, bid):
        """Invoke bid processing logic on incoming bid and send update to
        clients, or indicate illegal bid to single player.

        player_num (int): local player number
        bid (int): integer [0-5] of bid being made

        """
        # Check that player_num is active player.
        #----------------------------------------
        if player_num != self.gs.active_player:
            log.warning("Non-active player attempted to bid.")
            return None # Ignore
        bid_status = self.check_bid_legality(self.players[player_num], bid)
        if bid_status is False:
            return False # Not a legal bid; return False
                         # Game router will chastise appropriately.
        # Legal bid was made; update game state and log/publish.
        #-------------------------------------------------------
        elif bid_status == 'pass':
            pass    # Couldn't resist.
        elif bid_status == 'high':
            self.gs.high_bid = bid
            self.gs.declarer = player_num
        elif bid_status == 'cntr':
            self.gs.declarer = player_num # Set declarer; bid already Cinch.

        # Is bidding over? Either way, publish and return.
        if self.gs.active_player == self.gs.dealer: # Dealer always bids last
            self.gs.active_player = self.gs.declarer
            self.gs.game_mode = GAME_MODE.PLAY
            return self.publish('eob', player_num, bid)
        else:
            self.gs.active_player = self.gs.next_player(self.gs.active_player)
            return self.publish('bid', player_num, bid)

    def handle_card_played(self, player_num, card_num):
        """Invoke play processing logic on incoming play and send update to
        clients, or indicate illegal play to single player.

        player_num (int): local player number
        card_num (int): integer encoding of card being played by player

        """
        # Check that player_num is active player.
        #----------------------------------------
        if player_num != self.gs.active_player:
            log.warning("Non-active player attempted to play a card.")
            return None # Ignore

        if not (self.check_play_legality(self.players[player_num], card_num)):
            return False # Not a legal play; return False
                         # Game router will chastise appropriately.

        # Remove card from player's hand and put into play.
        #--------------------------------------------------
        for card_pos, card in list(enumerate(self.players[player_num].hand)):
            if card.code == card_num:
                a = self.players[player_num].hand.pop(card_pos)
                self.gs.cards_in_play.append(a)
                if self.gs.trump is None: # First card played this hand?
                    self.gs.trump = card.suit
                    self.gs.active_player = self.gs.next_player(
                                                    self.gs.active_player)
                    return self.publish('trp', player_num, card)
                break

        # Check for end of trick and handle, otherwise return.
        #-----------------------------------------------------
        winning_card = self.gs.trick_winning_card()
        if winning_card is None:
            # Trick is not over
            self.gs.active_player = self.gs.next_player(self.gs.active_player)
            return self.publish('crd', player_num, card)
        else:
            trick_winner = winning_card.owner
            self.gs.active_player = trick_winner
            self.gs.team_stacks[trick_winner
                                % TEAM_SIZE] += self.gs.cards_in_play
            self.gs.cards_in_play = []

        # Check for end of hand and handle, otherwise return.
        #----------------------------------------------------

        cards_left = len(self.players[0].hand)
        if cards_left != 0:
            # More tricks to play
            return self.publish('eot', player_num, card)

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
        gs.game_mode = GAME_MODE.BID
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
            message['mode'] = gs.game_mode

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

        if status in ['eog']:
            self.dbupdate()

        return output

    def start_game(self, plr_arg = ["Test0", "Test1", "Test2", "Test3"]):
        """Start a new game, deal first hands, and send msgs.

        plr_arg (dict): dict of player num, name pairs.
        """
        # Might as well error check this here. All games must have 4 players.
        if len(plr_arg) != NUM_PLAYERS:
            log.exception("Tried to start a game with <{0} players."
                          "".format(NUM_PLAYERS))

        self.players = [Player(x, plr_arg[x]) for x in range(NUM_PLAYERS)]
        self.gs = GameState(self.generate_id())
        self.deal_hand()
        self.gs.active_player = self.gs.next_player(self.gs.dealer)
        self.gs.game_mode = GAME_MODE.BID
        self.gs.trump = None

        return self.publish('sog', None, None)

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
            mode=self.gs.game_mode,
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
