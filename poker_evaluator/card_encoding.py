"""
poker_evaluator/card_encoding.py

Cards are represented as an int.

A = 14, K = 13, Q = 12, J = 11
Spades = 0, Hearts = 1, Diamonds = 2, Clubs = 3
"""

SPADES = 0
HEARTS = 1
DIAMONDS = 2
CLUBS = 3

RANK_MAP = {'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14} | {x: int(x) for x in "23456789"}
SUIT_MAP = {'s': 0, 'h': 1, 'd': 2, 'c': 3, 'S': 0, 'H': 1, 'D': 2, 'C': 3}

RANK_CHARS = 'XX23456789TJQKA'
SUIT_CHARS = 'shdc'


def card_from_str(s: str) -> int:
    """
    Parse a card string in standard poker notation.
    
    Examples: "Ah", "Ts", "2d", "Kc", "TD"
    """
    if len(s) != 2:
        raise ValueError(f"Invalid card string: {s!r} (expected 2 chars)")

    rank_char, suit_char = s[0], s[1]
    if rank_char not in RANK_MAP or suit_char not in SUIT_MAP:
        raise ValueError(f"Invalid card: {s!r}")
    
    rank = RANK_MAP[rank_char]
    suit = SUIT_MAP[suit_char]
    return card_to_int(rank, suit)

def card_to_int(rank: int, suit: int) -> int:
    if not (2 <= rank <= 14):
        raise ValueError(f"Invalid rank: {rank}")
    if not (0 <= suit <= 3):
        raise ValueError(f"Invalid suit: {suit}")
    return (rank << 4) | suit

# Not actually used to save on function-call overhead
def int_to_rank(card: int) -> int:
    return card >> 4

# Not actually used to save on function-call overhead
def int_to_suit(card: int) -> int:
    return card & 0xF

def standard_deck() -> list[Card]:
    """Return a list of all 52 standard cards."""
    ranks = list(range(2, 15))
    suits = [CLUBS, DIAMONDS, HEARTS, SPADES]
    return [card_to_int(r, s) for r in ranks for s in suits]


def short_deck() -> list[Card]:
    """Return a short deck (no twos, three, fours, or fives)."""
    ranks = list(range(6, 15))
    suits = [CLUBS, DIAMONDS, HEARTS, SPADES]
    return [card_to_int(r, s) for r in ranks for s in suits]
