#!/usr/bin/python3
"""
Game object for managing game properties, players, and game states.

TODO: game logging functionality
      pickling game for later recovery

"""
import random
from datetime import datetime, timezone

#this allows game.py to be ran alone from core dir AND as part of cinch.py
# for development.
## once final, will use only absolute imports (core.*)
try:
    import common as common
    from player import Player
    import cards
    from gamestate import GameState
except ImportError:
    import core.common as common
    from core.player import Player
    import core.cards as cards
    from core.gamestate import GameState    

#Constants and global variables
STARTING_HAND_SIZE = 9
NUM_TEAMS = 2
TEAM_SIZE = 2
NUM_PLAYERS = NUM_TEAMS * TEAM_SIZE
GAME_MODE = common.enum(PLAY=1, BID=2)

# Bid constants
BID = common.enum(PASS=0, CINCH=5)


class Game:
    """
    Define object for Game object with instance variables:
        id (integer): unique id for game object
        mode (integer): setting for game mode
        players (list): array of Player objects for players in game
        teams (dict): player id : local player num pairings (?)
        gs (object): current game state
        deck (object): Deck object containing Card objects
        
    """
    def __init__(self): #pass newGame params as args (??)
        self.id = 0     #TODO: have external counter for this
        self.players = []
        self.gs = None
        self.deck = cards.Deck()

    def __repr__(self):
        """Return descriptive string when asked to print object."""
        return "Cinch game with players: "+", ".join(str(_.name) for _ in
                                                     self.players)

    def check_bid_legality(self, player, bid):
        """Check a proposed bid for legality against the current gs. Assumes
        that player is indeed the active player. Returns a string indicating
        the bid type, or False if illegal bid.

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
        ##MJG: I just added the card.code functionality for convenience.
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
        if card.suit is self.gs.trump:
            return True      # Trump is always OK
        if card.suit is self.gs.cards_in_play[0].suit:
            return True      # Not trump, but followed suit.
        for each_card in player.hand:
            if each_card.suit is self.gs.cards_in_play[0].suit:
                return False # Could have followed suit with a different card.
        return True          # Couldn't follow suit, throwing off.
        
    def deal_hand(self):
        """Deal new hand to each player and set card ownership."""
        for player in self.players:
            player.hand = sorted([self.deck.deal_one() for x in range
                          (STARTING_HAND_SIZE)], reverse = True)
            
            for card in player.hand:
                card.owner = player.pNum

    def handle_bid(self, player_num, bid):
        """Invoke bid processing logic on incoming bid and send update to
        clients, or indicate illegal bid to single player.

        player_num (int): local player number
        bid (int): integer [0-5] of bid being made

        """
        # Check that player_num is active player.
        #----------------------------------------
        if player_num is not self.gs.active_player:
            print("Non-active player attempted to bid.") # Debugging
            return None # Ignore
        bid_status = self.check_bid_legality(self.players[player_num], bid)
        if bid_status is False:
            return False # Not a legal bid; return False
                         # Game router will chastise appropriately.
        # Legal bid was made; update game state and log/publish.
        #-------------------------------------------------------
        elif bid_status is 'pass':
            pass    # Couldn't resist.
        elif bid_status is 'high':
            self.gs.high_bid = bid
            self.gs.declarer = player_num
        elif bid_status is 'cntr':
            self.gs.declarer = player_num # Set declarer; bid already cinch.
            self.gs.countercinch = True
            
        # Is bidding over? Either way, publish and return.
        if self.gs.active_player == self.gs.dealer: # Dealer always last to bid
            self.gs.active_player = self.gs.declarer
            self.gs.game_mode = GAME_MODE.PLAY
            return self.publish('eob', player_num, bid)
        else:
            self.gs.active_player = self.gs.next_player(self.gs.active_player)
            return self.publish('bid', player_num, bid)
            
        raise NotImplementedError("Bid handling incomplete") # Debugging.
                
    def handle_card_played(self, player_num, card_num):
        """Invoke play processing logic on incoming play and send update to
        clients, or indicate illegal play to single player.
        
        Game router will ensure message follows Comm Structure contract, so
        formatting data here IAW those guidelines is optional but a good idea.
        
        player_num (int): local player number
        card_num (int): integer encoding of card being played by player

        """
        # Check that player_num is active player.
        #----------------------------------------
        if player_num is not self.gs.active_player:
            print("Non-active player attempted to play a card.") # Debugging
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
        
        # This is error checking to verify that all players have equal hand
        # sizes. Later, we can just check players[0].hand for cards.
        cards_left = 0
        for player in self.players:
            cards_left += len(player.hand)
        if cards_left % NUM_PLAYERS != 0:
            raise RuntimeError("Cards in hand not even.")
        if cards_left != 0:
            # More tricks to play
            return self.publish('eot', player_num, card)
            
        # Log hand results and check victory conditions.
        self.gs.score_hand()
        victor = False
        for score in self.gs.scores:
            if score >= 11:
                victor = True
                break
        
        # This block breaks if there are more than two teams.        
        if victor:
            if self.gs.scores[self.gs.declarer % TEAM_SIZE] >= 11:
                self.gs.winner = self.gs.declarer % TEAM_SIZE
            else:
                self.gs.winner = (self.gs.declarer + 1) % TEAM_SIZE
            return self.publish('eog', player_num, card)
                
        # If no victor, set up for next hand.
        self.gs.team_stacks = [[] for _ in range(NUM_TEAMS)]
        self.gs.dealer = self.gs.next_player(self.gs.dealer)
        self.gs.declarer = self.gs.dealer
        self.deck = cards.Deck()
        self.deal_hand()
        self.gs.active_player = self.gs.next_player(self.gs.dealer)
        self.gs.high_bid = 0
        self.gs.game_mode = GAME_MODE.BID
        self.gs.trump = None
        self.gs.countercinch = False

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
        
        # Initialize the output. Message always contains actvP, so do it here.
        gamelog = open('logs/'+str(self.gs.game_id)+'.log', 'a')
        message = {'actvP': self.gs.active_player}
        
        if status in ['sog', 'eob', 'eoh']:
            # Handle switching game modes first.
            message['mode'] = self.gs.game_mode
            
        if status in ['trp', 'crd', 'eot', 'eoh', 'eog']:
        
            if status is 'trp':
                message['trp'] = self.gs.trump
                # Player declared Suit as trump.
                print(self.players[pNum].name, "declared",
                      cards.SUITS_BY_NUM[self.gs.trump], "as trump.",
                      file=gamelog)
                      
            message['playC'] = data.code
            # Player played Card.
            print(self.players[pNum].name, "played", ''.join([str(data), "."]),
                  file=gamelog)
            
            if status in ['eot', 'eoh', 'eog']:
                message['remP'] = self.gs._t_w_card.owner
                # Player won the trick with Card.
                print(self.players[message['remP']].name,
                      "won the trick with", ''.join([str(self.gs._t_w_card),
                      "."]), file=gamelog)
                
                if status in ['eoh', 'eog']:
                    message['mp'] = ['',]*NUM_TEAMS # Initialize
                    # We will end up with a list of NUM_TEAMS strings,
                    # where the string is the match points out of 'hljg' won.
                    message['mp'][self.gs._results['high_holder']] += 'h'
                    message['mp'][self.gs._results['low_holder']] += 'l'
                    try:
                        message['mp'][self.gs._results['jack_holder']] += 'j'
                    except TypeError: # No jack out, NoneType.
                        pass
                    try:
                        message['mp'][self.gs._results['game_holder']] += 'g'
                    except TypeError: # Game tied and not awarded, NoneType.
                        pass
                    message['gp'] = self.gs._results['game_points']
                    message['sco'] = self.gs.scores
                    
                    # Hand results:
                    # -------------
                    # Team Team0: High Low [Game Points: 20]
                    # Team Team1: Jack Game [Game Points: 28]
                    # Declarer [was set|made bid].
                    # 
                    # New scores: 2, 2
                    #
                    print("Hand results:\n-------------", file=gamelog)
                    for num in range(NUM_TEAMS):
                        print("Team ", self.players[num].name, ": ", sep='',
                              end='', file=gamelog)
                        if self.gs._results['high_holder'] == num:
                            print("High ", end='', file=gamelog)
                        if self.gs._results['low_holder'] == num:
                            print("Low ", end='', file=gamelog)
                        if self.gs._results['jack_holder'] == num:
                            print("Jack ", end='', file=gamelog)
                        if self.gs._results['game_holder'] == num:
                            print("Game ", end='', file=gamelog)
                        print("[Game points: ",
                              self.gs._results['game_points'][num], "]",
                              sep='', file=gamelog)
                    # Blank lines intentional
                    if self.gs._results['declarer_set']:
                        print("Declarer was set.\n", file=gamelog)
                    else:
                        print("Declarer made bid.\n", file=gamelog)
                    print("New scores:", self.gs.scores, file=gamelog)
                    
                    if status is 'eog':
                        message['win'] = self.gs.winner
                        # Team TeamW wins!
                        print("Team", self.players[self.gs.winner].name,
                              "wins!", file=gamelog)
                        print(datetime.now(timezone.utc), file=gamelog)
                        print("################################", file=gamelog)
                    else: # Status must be 'eoh': Set up for next hand.
                        message['dlr'] = self.gs.dealer
                        # Player deals.
                        print(self.players[self.gs.dealer].name, "deals.",
                              file=gamelog)
                        output = [message.copy() for _ in range(NUM_PLAYERS)]
                        for player in self.players:
                            output[player.pNum]['addC'] = [card.code for card
                                                           in player.hand]
                            print(player.name, "\'s hand: ", sep='', end = '',
                                  file=gamelog)
                            print(", ".join(str(card) for card in player.hand),
                                  file=gamelog)
                            output[player.pNum]['tgt'] = [player.pNum]
            
        elif status in ['bid', 'eob']:
            message['bid'] = data
            if self.gs.countercinch:
                # Dealer Player counter-cinches!
                print("Dealer", self.players[self.gs.dealer].name,
                      "counter-cinches!", file=gamelog)
            else:
                if data == BID.PASS:
                    # Player passes.
                    print(self.players[pNum].name, "passes.", file=gamelog)
                elif data == BID.CINCH:
                    # Player cinches.
                    print(self.players[pNum].name, "cinches.", file=gamelog)
                else:
                    # Player bid X.
                    print(self.players[pNum].name, "bids", 
                          ''.join([str(data), "."]), file=gamelog)

        # Start of game is the same as end of hand except there are different
        # logging requirements, so there's a little bit of duplicated code.
        elif status is 'sog':
            print(datetime.now(timezone.utc), file=gamelog)
            print(self, file=gamelog)
            print("Game ID:", self.gs.game_id, "\n", file=gamelog)
            message['dlr'] = self.gs.dealer
            # Player deals.
            print(self.players[self.gs.dealer].name, "deals.",
                  file=gamelog)
            output = [message.copy() for _ in range(NUM_PLAYERS)]
            for player in self.players:
                output[player.pNum]['addC'] = [card.code for card
                                               in player.hand]
                print(player.name, "\'s hand: ", sep='', end = '',
                      file=gamelog)
                print(", ".join(str(card) for card in player.hand),
                      file=gamelog)
                output[player.pNum]['tgt'] = [player.pNum]        
            
        # Note: New hands are handled differently from all others because they
        # are the only ones dealing with private information. If status is
        # 'eoh'/'sog', output will be a length-4 list containing 4 dicts with
        # 'tgt' containing an integer, and 'addC' containing the new hands. If
        # not, output will be a length-1 list containing 1 dict with 'tgt' con-
        # taining a length-4 list. (With 4 meaning NUM_PLAYERS, of course.)
        if status not in ['eoh', 'sog']:
            message['tgt'] = [i for i in range(NUM_PLAYERS)]
            output = [message]
        
        gamelog.flush()
        gamelog.close()
        
        # TODO These print statements for debugging/testing only.
        #print("************",
        #      self.players[self.gs.active_player].name, "is next to act.",
        #      "************")
        
        return output


    def start_game(self, game_id=0):
        """Start game with id game_id, deal first hands, and send msgs.
        
        game_id (int): Assigned by game router. Defaults to 0 for testing.
        """
        self.players = [Player(x, game_id, "Test"+str(x))
                        for x in range(NUM_PLAYERS)]
        self.gs = GameState(game_id)
        self.deck = cards.Deck()
        self.deal_hand()
        self.gs.active_player = self.gs.next_player(self.gs.dealer)
        self.gs.game_mode = GAME_MODE.BID
        self.gs.countercinch = False
        self.gs.trump = None

        return self.publish('sog', None, None)
        
#test
if __name__ == '__main__': 
    print("Creating new game with 4 players.")
    g = Game()
    g.start_game(4000)
    g.handle_bid(g.gs.active_player, 0)
