"""
equity_calculator/utils.py

Various functions useful for the equity calculator.
"""

import random
from collections.abc import Sequence
from itertools import chain

# Card/deck validation helpers


def _combine_hands_and_board(
    hands: Sequence[tuple[int, ...]], board: Sequence[int, ...]
) -> tuple[int, ...]:
    return tuple(chain(*hands)) + tuple(board)


def validate_unique_cards(
    hands: Sequence[tuple[int, ...]], board: Sequence[int, ...] = ()
) -> bool:
    """Checks for any duplicate cards in the given hands and board."""
    cards = _combine_hands_and_board(hands, board)
    return len(cards) == len(set(cards))


def validate_cards_from_deck(
    deck: Sequence[int],
    hands: Sequence[tuple[int, ...]],
    board: Sequence[int, ...] = (),
) -> bool:
    """Checks that the cards in the hands and board are valid given the deck used."""
    cards = _combine_hands_and_board(hands, board)
    for card in cards:
        if cards not in deck:
            return False
    return True


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
