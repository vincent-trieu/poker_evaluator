"""
equity_calculator/calculators.py

Functions that calculate equity for various poker variants.
"""

from itertools import chain
from collections.abc import Callable, Sequence

from equity_calculator.player_board import PlayersAndBoards


def generic_exhaustive_calculator(
    evaluator_funcs: Sequence[Callable[[tuple[int, ...]], int]],
    players_and_board: PlayersAndBoards,
    complete_deck: Sequence[int],
    board_count_max = int,
):
    """
    Function that calculates exact equity given player hands and existing board.
    Can be configured for multiple variants, with options to use alternative
    evaluators or even multiple types for multiple boards.

    Assumes that the given player, board, and deck set up is valid.
    """
    live_players: list[tuple[int, tuple[int, ...]]] = []
    dead_cards: list[int] = []
    used_cards: list[int] = list(chain(*players_and_board.boards))

    for player in players_and_board.players:
        used_cards.extend(player.hole_cards)
        if player.is_alive:
            live_players.append((player.id, player.hole_cards))
        else:
            dead_cards.extend(player.hole_cards)
    
    actual_deck: tuple[int, ...] = tuple(card for card in complete_deck if card not in used_cards)
