"""
equity_calculator/calculators.py

Functions that calculate equity for various poker variants.
"""

from collections.abc import Callable, Sequence

from equity_calculator.player_board import PlayersAndBoards


def generic_exhaustive_calculator(
    evaluator_funcs: Sequence[Callable[[tuple[int, ...]], int]],
    players_and_board: PlayersAndBoards,
    deck: Sequence[int],
):
    """
    Function that calculates exact equity given player hands and existing board.
    Can be configured for multiple variants, with options to use alternative
    evaluators or even multiple types for multiple boards.
    """
    print("hi")
