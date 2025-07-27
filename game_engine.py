import random

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

