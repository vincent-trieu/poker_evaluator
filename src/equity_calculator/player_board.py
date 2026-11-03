"""
equity_calculator/player_board.py

Classes representing a player and their hole cards, and the board.
"""

from collections import namedtuple


class Player(namedtuple):
    """Immutable player state for equity calculation."""
    id: int
    hole_cards: tuple[int, ...]
    is_alive: bool


class PlayersAndBoards(namedtuple):
    """Immutable player and board state for equity calculation."""
    players: tuple[Player, ...]
    boards: tuple[tuple[int, ...], ...]
