"""
poker_evaluator/evaluator.py

This evaluator works by taking a pool of cards and working out what the best hand is
that can be constructed from them. This hand is not necessarily five cards.

This allows a level of flexibility that allows the evaluator to work with games
like Badugi, which don't use the standard 5-card hand rankings.
"""

from itertools import combinations
from typing import Callable

def hand_rank_code(hand_category: int, card_ranks: tuple[int, ...], size: int):
    """
    Function that returns an encoding of a hand and its ranking, as a comparable int.
    Better cards must be at the front.

    Type represents what category of hand it is e.g. flush, straight, and how good it is in the poker variant.
    Card ranks are there to differentiate between hands of the same kind e.g. a king-high straight vs a
    ten-high straight.

    The encoding works by using a number in base16 - the largest digit is the type of hand, then the
    next digit represents what kind of pair/straight/flush/etc. it is, and the other digits are the
    kickers in descending order.

    This means that we can compare hands simply by seeing which number is larger. For variants like Badugi
    where not every card in the hand is counted, the "smaller" hands have fewer digits and therefore lose
    to "bigger" hands.

    A larger number beats a smaller number.
    """
    code = hand_category
    for i in range(size):
        code = (code << 4) + (card_ranks[i] if i < len(card_ranks) else 0)
    return code

def rank_counts(cards) -> dict:
    """Takes a sequence of cards and returns a dict of the number seen of each rank."""
    counts: dict = {}
    for c in cards:
        counts[c.rank] = counts.get(c.rank, 0) + 1
    return counts

def is_flush(cards: tuple[Card, Card, Card, Card, Card]) -> bool:
    """Checks if the cards are all the same suit."""
    return len({c.suit for c in cards}) == 1

def straight_high(
    cards: tuple[Card, Card, Card, Card, Card], sequences: tuple[tuple[int, int, int, int, int], ...]
) -> int | None:
    """High card of the straight, or None."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")
    rank_set = {c.rank for c in cards}
    if len(rank_set) != 5:
        return None
    best = None
    for seq in sequences:
        if set(seq) == rank_set:
            high = max(seq)
            if best is None or high > best:
                best = high
    return best

def best_of_subsets(
    pool: Tuple[Card, ...],
    size_of_subsets: int,
    ranking_func: Callable[[Tuple[Card, ...]], int],
) -> int:
    """Maximum rank code over all size-k subsets of the pool."""
    best = None
    for subset in combinations(pool, size_of_subsets):
        code = ranking_func(subset)
        if best is None or code > best:
            best = code
    return best

_WHEEL = (14, 5, 4, 3, 2)
_STANDARD_SEQS = tuple(tuple(range(low, low + 5)) for low in range(2, 11)) + (_WHEEL,)

def standard_ranking(cards: tuple[Card, Card, Card, Card, Card]) -> int:
    """Rank a 5-card set under the usual rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    groups = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))
    shape = tuple(cnt for _, cnt in groups)
    group_ranks = [rank for rank, _ in groups]

    flush = is_flush(cards)
    str_high = straight_high(cards, _STANDARD_SEQS)

    if flush and str_high is not None:
        return hand_rank_code(8, [str_high], 5)
    if shape == (4, 1):
        return hand_rank_code(7, group_ranks, 5)
    if shape == (3, 2):
        return hand_rank_code(6, group_ranks, 5)
    if flush:
        return hand_rank_code(5, sorted((c.rank for c in cards), reverse=True), 5)
    if str_high is not None:
        return hand_rank_code(4, [str_high], 5)
    if shape == (3, 1, 1):
        return hand_rank_code(3, group_ranks, 5)
    if shape == (2, 2, 1):
        return hand_rank_code(2, group_ranks, 5)
    if shape == (2, 1, 1, 1):
        return hand_rank_code(1, group_ranks, 5)
    if shape == (1, 1, 1, 1, 1):
        return hand_rank_code(0, group_ranks, 5)
    raise AssertionError(f"unreachable shape {shape}")

def evaluate_standard(pool: Tuple[Card, ...]) -> int:
    """Best 5-card hand from a pool (Hold'em, stud, Omaha, etc.)."""
    return best_of_subsets(pool, 5, standard_ranking)
