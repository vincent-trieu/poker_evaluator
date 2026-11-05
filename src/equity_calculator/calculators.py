"""
equity_calculator/calculators.py

Functions that calculate equity for various poker variants.
"""

from collections.abc import Callable, Iterator, Sequence
from itertools import chain, combinations

from equity_calculator.player_board import PlayersAndBoards


def generic_exhaustive_calculator(
    evaluator_funcs: Sequence[Callable[[tuple[int, ...]], int]],
    players_and_boards: PlayersAndBoards,
    complete_deck: Sequence[int],
    board_count_max: int,
) -> dict[int, float]:
    """
    Function that calculates exact equity given player hands and existing board.
    Can be configured for multiple variants, with options to use alternative
    evaluators or even multiple types for multiple boards.

    Assumes that the given player, board, and deck set up is valid.
    """
    boards: tuple[tuple[int, ...], ...] = players_and_boards.boards

    if len(evaluator_funcs) != len(boards):
        raise ValueError(
            f"Number of evaluators is not equal to number of boards. There are {len(evaluator_funcs)} and {len(boards)} boards."
        )

    live_players: list[tuple[int, tuple[int, ...]]] = []
    used_cards: list[int] = list(chain(*boards))

    # Calculate cards still left in deck
    for player in players_and_boards.players:
        used_cards.extend(player.hole_cards)
        if player.is_alive:
            live_players.append((player.id, player.hole_cards))
    actual_deck: tuple[int, ...] = tuple(
        card for card in complete_deck if card not in used_cards
    )

    # Find number of cards needed to complete every board
    draws_required_per_board: tuple[int, ...] = tuple(
        board_count_max - len(board) for board in boards
    )
    draws_required_total = sum(draws_required_per_board)
    if draws_required_total > len(actual_deck):
        raise ValueError(
            f"Not enough cards in deck to complete boards. Deck has {len(actual_deck)} cards left; {draws_required_total} draws required."
        )

    player_wins: dict[int, float] = {player[0]: 0.0 for player in live_players}
    # Calculate all possible runouts given the given configuration
    for deal in potential_deals(actual_deck, draws_required_per_board):
        runout: tuple[tuple[int, ...], ...] = tuple(
            boards[board_id] + deal[board_id] for board_id in range(len(boards))
        )
        # Evaluate every runout and calculate equity for each live player
        for board_id, board_runout in enumerate(runout):
            eval_function = evaluator_funcs[board_id]
            leading_players: list[int] = []
            leading_code = None
            # Find winners of this board
            for player in live_players:
                hand_code = eval_function(player[1] + board_runout)
                if leading_code is None or hand_code > leading_code:
                    leading_players = [player[0]]
                    leading_code = hand_code
                elif hand_code == leading_code:
                    leading_players.append(player[0])
            # Distribute equity to leading players (they must be winners at end of loop)
            for winner in leading_players:
                player_wins[winner] += 1 / len(leading_players)

    # Normalise over possible runouts
    total_wins = sum(player_wins.values())
    return {
        player_id_wins[0]: player_id_wins[1] / total_wins
        for player_id_wins in player_wins.items()
    }


def potential_deals(
    deck: tuple[int, ...], draws_required_per_board: tuple[int, ...]
) -> Iterator[tuple[tuple[int, ...], ...]]:
    """Enumerates what combinations boards can have given the deck and draws needed."""
    if not draws_required_per_board:
        yield ()
        return
    k, rest_of_draws_required = (
        draws_required_per_board[0],
        draws_required_per_board[1:],
    )
    for first in combinations(deck, k):
        used_cards = set(first)
        remaining_cards = tuple(c for c in deck if c not in used_cards)
        for tail in potential_deals(remaining_cards, rest_of_draws_required):
            yield (first,) + tail
