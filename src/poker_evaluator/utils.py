"""
poker_evaluator/utils.py

Various functions and constants used in the evaluator code.
"""

from collections.abc import Callable, Iterable, Sequence

from poker_evaluator.card_encoding import SUITS, card_to_int

# Deck generating functions


def standard_deck() -> list[int]:
    """Return a list of all 52 standard cards."""
    ranks = list(range(2, 15))
    return [card_to_int(r, s) for r in ranks for s in SUITS]


def short_deck() -> list[int]:
    """Return a short deck (no twos, three, fours, or fives)."""
    ranks = list(range(6, 15))
    return [card_to_int(r, s) for r in ranks for s in SUITS]


# Hand rank encoding functions


def hand_rank_code(
    hand_category: int, card_ranks: Sequence[int], size: int
) -> tuple[int, int]:
    """
    Function that returns an encoding of a hand and its ranking, as a comparable int.
    Better cards must be at the front.

    Type represents what category of hand it is e.g. flush, straight, and how good it is in the poker variant.
    Card ranks are there to differentiate between hands of the same kind e.g. a king-high straight vs a
    ten-high straight.

    The encoding works by using a number in base16 - the largest digit is the type of hand, then the
    next digit represents what kind of pair/straight/flush/etc. it is, and the other digits are the
    kickers in descending order.

    This means that we can compare hands simply by seeing which number is larger (better). For variants like
    Badugi where not every card in the hand is counted, the "smaller" hands have fewer digits and therefore
    lose to "bigger" hands.
    """
    code = hand_category
    for i in range(size):
        code = (code << 4) + (card_ranks[i] if i < len(card_ranks) else 0)
    return code


def hrc_category_filtered(
    hand_category: int,
    card_ranks: Sequence[int],
    size: int,
    leading_hand_category: int,
) -> tuple[int, int]:
    """
    Version of hand_rank_code but if the hand_category is smaller than the leading_hand_category, the code
    calculation is skipped and
    """
    if leading_hand_category > hand_category:
        return (0, 0)
    return (hand_rank_code(hand_category, card_ranks, size), hand_category)


# Rank-related helper functions


def rank_counts(cards: Iterable[int]) -> list[tuple[int, int]]:
    """
    Takes a sequence of cards and returns a tuple of the number seen of each rank.

    Note that the ordering is highest count, then highest rank. In particular, if each card has a different
    rank, the ranks will be sorted in reverse order.
    """
    counts = [0] * 15
    for c in cards:
        counts[c >> 4] += 1
    groups = sorted(((cnt, r) for r, cnt in enumerate(counts) if cnt), reverse=True)
    return groups


def rank_mask(ranks: Iterable[int]) -> int:
    """
    Produces a bitmask of the ranks of the cards (ints) given.
    Positions are offset by two compared to rank.
    """
    m = 0
    for r in ranks:
        # Smallest rank is 2
        m |= 1 << (r - 2)
    return m


# Evaluation helpers


def best_of_subsets(
    subsets: Iterable[tuple[int, ...]],
    ranking_func: Callable[[tuple[int, ...]], int],
    cache: dict[tuple[int, ...], int] | None = None,
    allow_none: bool = False,
) -> int | None:
    """
    Maximum rank code over all subsets of cards given.

    Subsets should be consistently ordered for best performance.
    """
    if cache is None:
        cache = {}
    best = None
    leading_hand_category = 0
    for subset in subsets:
        cached_code = cache.get(subset)
        if cached_code != None:
            if best is None or cached_code > best:
                best = cached_code
        else:
            (code, hand_category) = ranking_func(subset, leading_hand_category)
            if (
                code != 0
            ):  # i.e. it wasn't skipped by leading_hand_category being too small
                cache[subset] = code
            if best is None or code > best:
                leading_hand_category = hand_category
                best = code
    if best is None and allow_none is False:
        raise ValueError(f"No subset valid as a hand: {subsets!r}")
    return best
