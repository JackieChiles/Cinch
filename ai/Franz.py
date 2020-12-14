#!/usr/bin/python3
"""Franz, Arch-Duke of Cinch"""

# Import base class for AI agent
from ai.base import AIBase, log

AI_CLASS = "Franz" # Set this to match the class name for the agent
__author__  = "JACK!"
__version__ = "1.0"
__date__    = "29 June 2014"
__skill__   = "2"
__agent_name__  = "Franz"
__description__ = "Tries to be reasonable but will probably lose to a Serbian in the end."


class Franz(AIBase):
    def __init__(self, room, seat):
        super(Franz, self).__init__(room, seat, self.identity)  # Call to parent init
        self.start() # Blocks

    def bid(self):
        """Overriding base class bid."""
        # For each potential trump suit, determine value of hand.
        # Jack of trump is worth 0.25 per trump (includes itself) up to 1.
        # Add up values of all hand cards.

        TRUMP_RANK_VALUES = {14:1, 13:0.3, 12:0.2, 11:0, 10:0.1, 9:0.1, 8:0.1,
                             7:0.1, 6:0.1, 5:0.1, 4:0.1, 3:0.2, 2:1}
        OFF_RANK_VALUES = {14:0.2, 13:0.15, 12:0.1, 11:0.05, 10:0, 9:0, 8:0, 7:0,
                           6:0, 5:0, 4:0, 3:0, 2:0}
        hand_values = [0,0,0,0]
        for suit in range(4):
            num_trump = 0 # Count up to see how strong the trump jack would be.
            trump_jack = False # Change to True if detected
            for card in hand:
                if card.suit == suit:
                    num_trump += 1
                    if card.rank == 11: # Jack in potential trump suit.
                        trump_jack = True
                    hand_values[suit] += TRUMP_RANK_VALUES[card.rank]
                else:
                    hand_values[suit] += OFF_RANK_VALUES[card.rank]
            if trump_jack:
                hand_values[suit] += min(1.0, num_trump * 0.25)

        
        if self.is_legal_bid(proposed_bid):
            self.send_bid(proposed_bid)
        else:
            log.debug("BUG: Pass instead of bidding " + str(proposed_bid) + ".")
            self.send_bid(0)

    def play(self):
        """Overriding base class play."""
        # Figure out what plays are allowed.
        legal_cards = []
        for c in self.hand:
            if self.is_legal_play(c):
                legal_cards.append(c)
        log.debug(self.label + 'to play from choices: ' + str(legal_cards))
        
        #TODO implement real play logic
        chosen_card = legal_cards[0]

        # Choices should already be validated, so no need to check like in bid()
        self.send_play(chosen_card)

    def think(self):
        """Overriding base class think. This is optional and here to demo."""
        pass
