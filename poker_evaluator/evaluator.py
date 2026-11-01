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

def _subset_key(pool_subset: tuple[int, ...]) -> int:
    return sum(c << (8 * i) for i, c in enumerate(sorted(pool_subset)))

# Generic helpers

def rank_counts(cards) -> list[tuple[int, int], ...]:
    """Takes a sequence of cards and returns a tuple of the number seen of each rank."""
    counts = [0] * 15
    for c in cards:
        counts[c >> 4] += 1
    groups = sorted(((cnt, r) for r, cnt in enumerate(counts) if cnt), reverse=True)
    return groups

def is_flush(cards: tuple[int, int, int, int, int]) -> bool:
    """Checks if the cards are all the same suit."""
    suit_to_check = cards[0] & 0xF
    for card in cards[1:5]:
        if (card & 0xF) != suit_to_check:
            return False
    return True

def rank_mask(ranks) -> int:
    m = 0
    for r in ranks:
        m |= 1 << (r - 2)
    return m

def straight_high(
    cards: tuple[int, int, int, int, int], sequence_table: dict[int, int]
) -> int | None:
    """
    High card of the straight, or None.
    
    Assumes the sequences are in order from best to worst.
    """
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")
    m = 0
    for c in cards:
        m |= 1 << ((c >> 4) - 2)
    if m.bit_count() != 5:
        return None
    return sequence_table.get(m)

'''def best_of_subsets(
    pool: tuple[int, ...],
    size_of_subsets: int,
    ranking_func: Callable[[tuple[int, ...]], int],
) -> int:
    """Maximum rank code over all size-k subsets of the pool."""
    if len(pool) < size_of_subsets:
        raise ValueError(f"Invalid size: {pool!r} (expected at least {size_of_subsets} cards)")
    best = None
    leading_hand_category = 0
    for subset in combinations(pool, size_of_subsets):
        (code, hand_category) = ranking_func(subset, leading_hand_category)
        if best is None or code > best:
            leading_hand_category = hand_category
            best = code
    if best is None:
        raise ValueError(f"Cards have no subset valid as a hand: {pool!r}")
    return best'''

def best_of_subsets(
    subsets: tuple[tuple[int, ...], ...],
    ranking_func: Callable[[tuple[int, ...]], int],
    cache: dict[tuple[int, ...], int] = dict(),
) -> int:
    """
    Maximum rank code over all subsets of cards given.

    Subsets should be consistently ordered for best performance.
    """
    best = None
    leading_hand_category = 0
    for subset in subsets:
        cached_code = cache.get(subset)
        if cached_code != None:
            if best is None or cached_code > best:
                best = cached_code
        else:
            (code, hand_category) = ranking_func(subset, leading_hand_category)
            if code != 0: # i.e. it wasn't skipped by leading_hand_category being too small
                cache[subset] = code
            if best is None or code > best:
                leading_hand_category = hand_category
                best = code
    if best is None:
        raise ValueError(f"No subset valid as a hand: {subsets!r}")
    return best

# Standard poker

_WHEEL_STANDARD = (5, frozenset((14, 5, 4, 3, 2)))
_STRAIGHT_SEQS_STANDARD = tuple((low + 4, frozenset(range(low, low + 5))) for low in range(10, 1, -1)) + (_WHEEL_STANDARD,)
_STRAIGHT_BY_MASK_STANDARD = {rank_mask(ranks): high for high, ranks in _STRAIGHT_SEQS_STANDARD}

def ranking_standard(cards: tuple[int, int, int, int, int], leading_hand_category: int) -> tuple[int, int]:
    """Rank a 5-card set under the usual rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    shape = tuple(cnt for cnt, _ in counts)
    group_ranks = [rank for _, rank in counts]

    if shape == (4, 1):
        if leading_hand_category > 7:
            return (0, 0)
        return (hand_rank_code(7, group_ranks, 5), 7)
    if shape == (3, 2):
        if leading_hand_category > 6:
            return (0, 0)
        return (hand_rank_code(6, group_ranks, 5), 6)
    if shape == (3, 1, 1):
        if leading_hand_category > 3:
            return (0, 0)
        return (hand_rank_code(3, group_ranks, 5), 3)
    if shape == (2, 2, 1):
        if leading_hand_category > 2:
            return (0, 0)
        return (hand_rank_code(2, group_ranks, 5), 2)
    if shape == (2, 1, 1, 1):
        if leading_hand_category > 1:
            return (0, 0)
        return (hand_rank_code(1, group_ranks, 5), 1)
    if shape == (1, 1, 1, 1, 1):
        # Flushes and straights only possible with this shape
        flush = is_flush(cards)
        str_high = straight_high(cards, _STRAIGHT_BY_MASK_STANDARD)

        if flush and str_high is not None:
            return (hand_rank_code(8, [str_high], 5), 8)
        if flush:
            if leading_hand_category > 5:
                return (0, 0)
            return (hand_rank_code(5, sorted((c >> 4 for c in cards), reverse=True), 5), 5)
        if str_high is not None:
            if leading_hand_category > 4:
                return (0, 0)
            return (hand_rank_code(4, [str_high], 5), 4)
        if leading_hand_category > 0:
            return (0, 0)
        return (hand_rank_code(0, group_ranks, 5), 0)
    raise AssertionError(f"unreachable shape {shape}")

# Short deck poker

_WHEEL_SHORT_DECK = (9, frozenset((14, 9, 8, 7, 6)))
_STRAIGHT_SEQS_SHORT_DECK = tuple((low + 4, frozenset(range(low, low + 5))) for low in range(10, 5, -1))  + (_WHEEL_SHORT_DECK,)
_STRAIGHT_BY_MASK_SHORT_DECK = {rank_mask(ranks): high for high, ranks in _STRAIGHT_SEQS_SHORT_DECK}

def ranking_short_deck(cards: tuple[int, int, int, int, int], leading_hand_category: int) -> tuple[int, int]:
    """Rank a 5-card set under short deck rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    shape = tuple(cnt for cnt, _ in counts)
    group_ranks = [rank for _, rank in counts]

    if shape == (4, 1):
        if leading_hand_category > 7:
            return (0, 0)
        return (hand_rank_code(7, group_ranks, 5), 7)
    if shape == (3, 2):
        if leading_hand_category > 5:
            return (0, 0)
        return (hand_rank_code(5, group_ranks, 5), 5)
    if shape == (3, 1, 1):
        if leading_hand_category > 3:
            return (0, 0)
        return (hand_rank_code(3, group_ranks, 5), 3)
    if shape == (2, 2, 1):
        if leading_hand_category > 2:
            return (0, 0)
        return (hand_rank_code(2, group_ranks, 5), 2)
    if shape == (2, 1, 1, 1):
        if leading_hand_category > 1:
            return (0, 0)
        return (hand_rank_code(1, group_ranks, 5), 1)
    if shape == (1, 1, 1, 1, 1):
        flush = is_flush(cards)
        str_high = straight_high(cards, _STRAIGHT_BY_MASK_SHORT_DECK)

        if flush and str_high is not None:
            return (hand_rank_code(8, [str_high], 5), 8)
        # Flushes are better than full houses in short deck
        if flush:
            if leading_hand_category > 6:
                return (0, 0)
            return (hand_rank_code(6, sorted((c >> 4 for c in cards), reverse=True), 5), 6)
        if str_high is not None:
            if leading_hand_category > 4:
                return (0, 0)
            return (hand_rank_code(4, [str_high], 5), 4)
        return (hand_rank_code(0, group_ranks, 5), 0)
    raise AssertionError(f"unreachable shape {shape}")

# Ace to Five low

def ranking_ace_to_five_low(cards: tuple[int, int, int, int, int], leading_hand_category: int) -> tuple[int, int]:
    """Rank a 5-card set under Ace to Five low rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    shape = tuple(cnt for cnt, _ in counts)
    # Aces are low - invert all other cards
    group_ranks = [(14 if rank == 14 else (14 - rank)) for _, rank in counts]

    if shape == (4, 1):
        if leading_hand_category > 0:
            return (0, 0)
        return (hand_rank_code(0, group_ranks, 5), 0)
    if shape == (3, 2):
        if leading_hand_category > 1:
            return (0, 0)
        return (hand_rank_code(1, group_ranks, 5), 1)
    if shape == (3, 1, 1):
        if leading_hand_category > 2:
            return (0, 0)
        return (hand_rank_code(2, group_ranks, 5), 2)
    if shape == (2, 2, 1):
        if leading_hand_category > 3:
            return (0, 0)
        return (hand_rank_code(3, group_ranks, 5), 3)
    if shape == (2, 1, 1, 1):
        if leading_hand_category > 4:
            return (0, 0)
        return (hand_rank_code(4, group_ranks, 5), 4)
    if shape == (1, 1, 1, 1, 1):
        return (hand_rank_code(5, group_ranks, 5), 5)
    raise AssertionError(f"unreachable shape {shape}")

# Badugi

def legal_badugi(cards: tuple[int, ...]) -> bool:
    """Checks if a Badugi hand is legal (has no matching card ranks or suits)."""
    suits = [c & 0xF for c in cards]
    ranks = [c >> 4 for c in cards]
    return len(set(suits)) == len(suits) and len(set(ranks)) == len(ranks)

def ranking_badugi(cards: tuple[int, ...], leading_hand_category: int) -> tuple[int, int]:
    """Ranks a hand based on Badugi rules. Assumes it's a legal hand, otherwise the code is nonsense."""
    ranks = sorted((14 if (card >> 4) == 14 else (14 - (card >> 4)) for card in cards))
    return (hand_rank_code(0, ranks, len(cards)), 0)

# Specific poker variant evaluation functions

def evaluate_standard(pool: tuple[int, ...]) -> int:
    """Best 5-card hand from an n-card pool (e.g. Texas Hold'em)."""
    subsets = tuple(subset for subset in combinations(sorted(pool), 5))
    return best_of_subsets(subsets, ranking_standard)

def evaluate_short_deck(pool: tuple[int, ...]) -> int:
    """Best 5-card hand from an n-card pool (e.g. short deck Texas Hold'em)."""
    subsets = tuple(subset for subset in combinations(sorted(pool), 5))
    return best_of_subsets(subsets, ranking_short_deck)

def evaluate_ace_to_five_low(pool: tuple[int, ...]) -> int:
    """Best ('worst') 5-card hand from an n-card pool (e.g. Razz)."""
    subsets = tuple(subset for subset in combinations(sorted(pool), 5))
    return best_of_subsets(subsets, ranking_ace_to_five_low)

def evaluate_badugi(hand: tuple[int, int, int, int]) -> int:
    """
    Badugi evaluation of four cards.

    Tries size 4 first (a full Badugi), then 3, 2, 1. More cards beats fewer.
    """
    for size in (4, 3, 2, 1):
        best = None
        for subset in combinations(hand, size):
            if not legal_badugi(subset):
                continue
            (code, _) = ranking_badugi(subset, 0)
            if best is None or code > best:
                best = code
        if best is not None:
            return best
    raise AssertionError(f"no subset is legal in hand {hand!r}")
