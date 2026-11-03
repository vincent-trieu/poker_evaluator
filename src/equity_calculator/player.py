"""
equity_calculator/player.py

Class representing a player and their hole cards.
"""

from collections import namedtuple


class Player(namedtuple):
    """Immutable player state for equity calculation."""
    id: int
    hole_cards: tuple[int, ...]
