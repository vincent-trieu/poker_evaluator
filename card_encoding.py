"""
poker_evaluator/card.py

Cards are represented as a tuple of integers.

A = 14, K = 13, Q = 12, J = 11
Spades = 0, Hearts = 1, Diamonds = 2, Clubs = 3
"""

from dataclasses import dataclass

rank_map = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} | {x: int(x) for x in "23456789"}
suit_map = {'s': 0, 'h': 1, 'd': 2, 'c': 3}

@dataclass(frozen=True)
class Card:
    rank: int  # 2-14
    suit: int  # 0-3
    
    @classmethod
    def from_str(cls, s: str) -> 'Card':
        """Parse 'Ah', '2d', 'Ts', etc."""
        rank_char, suit_char = s[0], s[1]
        rank = rank_map.get(rank_char)
        return cls(rank, suit_map[suit_char])
    
    def __str__(self):
        rank_str = str(self.rank) if self.rank < 10 else {10:'T', 11:'J', 12:'Q', 13:'K', 14:'A'}[self.rank]
        suit_str = 'shdc'[self.suit]
        return f"{rank_str}{suit_str}"
