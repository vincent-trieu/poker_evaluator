"""
equity_calculator/utils.py

Various functions useful for the equity calculator.
"""

import random
from collections.abc import Sequence
from itertools import chain

from equity_calculator.player_board import PlayersAndBoards

# Card/deck validation helpers


def _combine_hands_and_boards(
    hands: Sequence[tuple[int, ...]], boards: Sequence[Sequence[int, ...]]
) -> tuple[int, ...]:
    return tuple(chain(*hands) + chain(*boards))


def validate_unique_cards(
    hands: Sequence[tuple[int, ...]], boards: Sequence[Sequence[int, ...]] = ()
) -> None:
    """Checks for any duplicate cards in the given hands and boards."""
    cards = _combine_hands_and_boards(hands, boards)
    if len(cards) != len(set(cards)):
        raise ValueError(
            f"Duplicate cards between hands and boards: hands = {hands!r} boards = {boards!r}"
        )


def validate_cards_from_deck(
    complete_deck: Sequence[int],
    hands: Sequence[tuple[int, ...]],
    boards: Sequence[int, ...] = (),
) -> None:
    """Checks that the cards in the hands and boards are valid given the deck used."""
    cards = _combine_hands_and_boards(hands, boards)
    for card in cards:
        if card not in complete_deck:
            raise ValueError(
                f"Card not found in deck: card = {card!r} deck = {complete_deck!r}"
            )


def validate_players_and_boards(
    players_and_boards: PlayersAndBoards,
    complete_deck: Sequence[int],
    hole_card_count: int,
    board_count_max: int,
) -> None:
    """Checks that the hole cards and board make sense, given the variant and deck used."""
    hands = tuple(player.hole_cards for player in players_and_boards.players)
    boards = players_and_boards.boards

    # Check each player has the right number of hole cards
    for hand in hands:
        if len(hand) != hole_card_count:
            raise ValueError(
                f"Invalid hole card count: {hand!r} (expected {hole_card_count} cards)"
            )

    # Check the boards don't have too many cards
    for board in boards:
        if len(board) > board_count_max:
            raise ValueError(
                f"Invalid board card count: {board!r} (expected at most {board_count_max} cards)"
            )

    validate_unique_cards(hands, boards)
    validate_cards_from_deck(complete_deck, hands, boards)

    # Check at least two players are live
    live_count = 0
    for player in PlayersAndBoards.players:
        if player.is_alive:
            live_count += 1
    if live_count < 2:
        raise ValueError(
            f"Fewer than two players are live: {players_and_boards.players!r}"
        )


# Deck helpers


def get_unknown_cards(
    deck: Sequence[int],
    known_sets: Sequence[tuple[int, ...]],
) -> tuple[int, ...]:
    """Return sorted tuple of cards not in any known set."""
    known = set()
    for ks in known_sets:
        known.update(ks)
    return tuple(c for c in deck if c not in known)


def sample_from_deck(
    rng: random.Random,
    draws_required: int,
    cards_in_deck: Sequence[int],
    board: Sequence[int, ...] = (),
) -> tuple[int]:
    """Samples cards from the deck and appends them to the board."""
    if draws_required == 0:
        return board

    if draws_required > len(cards_in_deck):
        raise ValueError(
            f"Not enough cards left in deck: need {draws_required}, have {len(cards_in_deck)}"
        )

    # Micro-optimization: direct sampling for k = 1
    if draws_required == 1:
        return board + random.choice(cards_in_deck)
    else:
        return tuple(board + rng.sample(cards_in_deck, draws_required))
