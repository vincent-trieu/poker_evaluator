"""
poker_evaluator/card.py

Cards are represented as a tuple of integers.

A = 14, K = 13, Q = 12, J = 11
Spades = 0, Hearts = 1, Diamonds = 2, Clubs = 3
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Card:
    """
    Cards are represented as a tuple of integers.

    Attributes:
        rank (int): A = 14, K = 13, Q = 12, J = 11, T = 10, 9 = 9 and so on
        suit (int): Spades = 0, Hearts = 1, Diamonds = 2, Clubs = 3
    """
    rank: int
    suit: int

    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3

    RANK_MAP = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} | {x: int(x) for x in "23456789"}
    SUIT_MAP = {'s': 0, 'h': 1, 'd': 2, 'c': 3, 'S': 0, 'H': 1, 'D': 2, 'C': 3}

    RANK_CHARS = 'XX23456789TJQKA'
    SUIT_CHARS = 'shdc'
    
    @classmethod
    def from_str(cls, s: str) -> 'Card':
        """
        Parse a card string in standard poker notation.
        
        Examples: "Ah", "Ts", "2d", "Kc", "as", "TD"
        """
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s!r} (expected 2 chars)")

        rank_char, suit_char = s[0], s[1]
        
        try:
            rank = cls.RANK_MAP[rank_char]
            suit = cls.SUIT_MAP[suit_char]
        except KeyError as e:
            raise ValueError(f"Invalid card character in {s!r}: {e}")

        return cls(rank, suit)
    
    def __str__(self):
        rank_str = self.RANK_CHARS[self.rank]
        suit_str = self.SUIT_CHARS[self.suit]
        return f"{rank_str}{suit_str}"
    
    def __repr__(self) -> str:
        return f"Card({self.rank}, {self.suit}) # {self}"
