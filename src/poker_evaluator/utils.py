"""
poker_evaluator/utils.py

Various functions and constants used in the evaluator code.
"""

from poker_evaluator.card_encoding import SUITS, card_to_int


def standard_deck() -> list[int]:
    """Return a list of all 52 standard cards."""
    ranks = list(range(2, 15))
    return [card_to_int(r, s) for r in ranks for s in SUITS]


def short_deck() -> list[int]:
    """Return a short deck (no twos, three, fours, or fives)."""
    ranks = list(range(6, 15))
    return [card_to_int(r, s) for r in ranks for s in SUITS]
