import random

# Card rank order
RANK_ORDER = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
SUITS = ['♣', '♦', '♥', '♠']

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def rank_value(self):
        return RANK_ORDER.index(self.rank)

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.passed = False

    def play_cards(self, cards):
        for card in cards:
            self.hand.remove(card)

    def has_card(self, rank):
        return any(card.rank == rank for card in self.hand)

    def is_hand_empty(self):
        return len(self.hand) == 0

class Game:
    def __init__(self, player_names):
        self.players = [Player(name) for name in player_names]
        self.turn_index = 0
        self.last_played = []
        self.same_count = 0
        self.last_player = None
        self.initialize_game()

    def initialize_game(self):
        # Create and shuffle deck
        deck = [Card(rank, suit) for rank in RANK_ORDER for suit in SUITS]
        random.shuffle(deck)

        # Distribute cards
        num_players = len(self.players)
        for i, card in enumerate(deck):
            self.players[i % num_players].hand.append(card)

        # Determine who has 3♣ and start with them
        for i, player in enumerate(self.players):
            for card in player.hand:
                if card.rank == '3' and card.suit == '♣':
                    self.turn_index = i
                    print(f"{player.name} has 3♣ and starts.")
                    return

    def display_player_hand(self, player):
        print(f"{player.name}'s hand: {sorted(player.hand, key=lambda c: c.rank_value())}")

    def is_valid_play(self, played_cards):
        if not played_cards:
            return False
        ranks = [card.rank for card in played_cards]
        if not all(r == ranks[0] for r in ranks):
            return False  # not same-rank cards
        if self.last_played:
            if len(played_cards) != self.same_count:
                return False
            if RANK_ORDER.index(ranks[0]) < RANK_ORDER.index(self.last_played[0].rank):
                return False
        return True

    def next_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.players)

    def play_turn(self):
    current = self.players[self.turn_index]
    if current.is_hand_empty():
        return True

    self.display_player_hand(current)
    print(f"{current.name}'s turn. Last played: {self.last_played} | same_count: {self.same_count}")
    move = input("Enter cards to play (e.g. 7♣ 7♦) or 'pass': ").strip()

    if move.lower() == "pass":
        current.passed = True

        active_players = [p for p in self.players if not p.passed and p != self.last_player]
        if not active_players:
            print("✅ All passed except last player. Round resets.")
            self.last_played = []
            self.same_count = 0
            for p in self.players:
                p.passed = False
            self.turn_index = self.players.index(self.last_player)
        else:
            self.next_turn()
    else:
        card_strs = move.split()
        try:
            selected_cards = [card for card in current.hand if f"{card.rank}{card.suit}" in card_strs]
            if self.is_valid_play(selected_cards):
                current.play_cards(selected_cards)
                self.last_played = selected_cards
                self.same_count = len(selected_cards)
                self.last_player = current
                print(f"{current.name} played: {selected_cards}")
                for p in self.players:
                    p.passed = False
                if current.is_hand_empty():
                    print(f"🎉 {current.name} wins the game!")
                    return True
                self.next_turn()
            else:
                print("❌ Invalid move. Try again.")
        except:
            print("⚠️ Error reading input. Try again.")

def start_game():
    num = int(input("Enter number of players (3–6): "))
    names = [input(f"Enter name for Player {i+1}: ") for i in range(num)]
    game = Game(names)

    over = False
    while not over:
        over = game.play_turn()

if __name__ == "__main__":
    start_game()
