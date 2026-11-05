"""
equity_calculator/calculators.py

Functions that calculate equity for various poker variants.
"""

from collections.abc import Callable, Sequence
from itertools import chain, permutations

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
    dead_cards: list[int] = []
    used_cards: list[int] = list(chain(*boards))

    for player in players_and_boards.players:
        used_cards.extend(player.hole_cards)
        if player.is_alive:
            live_players.append((player.id, player.hole_cards))
        else:
            dead_cards.extend(player.hole_cards)
    actual_deck: tuple[int, ...] = tuple(
        card for card in complete_deck if card not in used_cards
    )

    draws_required_per_board: tuple[int, ...] = tuple(
        board_count_max - len(board) for board in boards
    )
    draws_required_total = sum(draws_required_per_board)
    if draws_required_total > len(actual_deck):
        raise ValueError(
            f"Not enough cards in deck to complete boards. Deck has {len(actual_deck)} cards left; {draws_required_total} draws required."
        )
    potential_deals = permutations(actual_deck, draws_required_total)

    # Calculate all possible runouts given the given configuration
    potential_runouts: list[tuple[tuple[int, ...], ...]] = []
    for deal in potential_deals:
        i = 0
        runout: list[tuple[int, ...]] = []
        for board_id, draws_required in enumerate(draws_required_per_board):
            runout.append(boards[board_id] + deal[i:i + draws_required])
            i += draws_required
        potential_runouts.append(tuple(runout))

    # Evaluate every runout and calculate equity for each live player
    player_wins: dict[int, float] = {player[0]: 0.0 for player in live_players}
    for runout in potential_runouts:
        for board_id, board_runout in enumerate(runout):
            eval_function = evaluator_funcs[board_id]
            players_best_hand_code: dict[int, int] = {
                player[0]: eval_function(player[1] + board_runout)
                for player in live_players
            }
            best = max(players_best_hand_code.values())
            winners = [p[0] for p in players_best_hand_code.items() if p[1] == best]
            for winner in winners:
                player_wins[winner] += 1 / len(winners)

    return {player_id_wins[0]: player_id_wins[1] / len(potential_runouts) for player_id_wins in player_wins.items()}
