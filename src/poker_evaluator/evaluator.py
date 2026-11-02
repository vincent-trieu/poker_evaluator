"""
poker_evaluator/evaluator.py

This evaluator works by taking a pool of cards and working out what the best hand is
that can be constructed from them. This hand is not necessarily five cards.

This allows a level of flexibility that allows the evaluator to work with games
like Badugi, which don't use the standard 5-card hand rankings.
"""

from itertools import combinations

from poker_evaluator.utils import best_of_subsets, hand_rank_code, hrc_category_filtered

# Generic helpers


def rank_counts(cards) -> list[tuple[int, int], ...]:
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


def is_flush(cards: tuple[int, ...]) -> bool:
    """Checks if the cards are all the same suit."""
    suit_to_check = None
    for card in cards:
        if suit_to_check is None:
            suit_to_check = card & 0xF
        elif (card & 0xF) != suit_to_check:
            return False
    return True


def rank_mask(ranks) -> int:
    m = 0
    for r in ranks:
        # Smallest rank is 2
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


# Standard poker

_WHEEL_STANDARD = (5, frozenset((14, 5, 4, 3, 2)))
_STRAIGHT_SEQS_STANDARD = tuple(
    (low + 4, frozenset(range(low, low + 5))) for low in range(10, 1, -1)
) + (_WHEEL_STANDARD,)
_STRAIGHT_BY_MASK_STANDARD = {
    rank_mask(ranks): high for high, ranks in _STRAIGHT_SEQS_STANDARD
}


def ranking_standard(
    cards: tuple[int, int, int, int, int], leading_hand_category: int
) -> tuple[int, int]:
    """Rank a 5-card set under the usual rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    shape = tuple(cnt for cnt, _ in counts)
    group_ranks = [rank for _, rank in counts]

    if shape == (4, 1):
        return hrc_category_filtered(7, group_ranks, 5, leading_hand_category)
    if shape == (3, 2):
        return hrc_category_filtered(6, group_ranks, 5, leading_hand_category)
    if shape == (3, 1, 1):
        return hrc_category_filtered(3, group_ranks, 5, leading_hand_category)
    if shape == (2, 2, 1):
        return hrc_category_filtered(2, group_ranks, 5, leading_hand_category)
    if shape == (2, 1, 1, 1):
        return hrc_category_filtered(1, group_ranks, 5, leading_hand_category)
    if shape == (1, 1, 1, 1, 1):
        # Flushes and straights only possible with this shape
        flush = is_flush(cards)
        str_high = straight_high(cards, _STRAIGHT_BY_MASK_STANDARD)

        if flush and str_high is not None:
            return (hand_rank_code(8, [str_high], 5), 8)
        if flush:
            return hrc_category_filtered(5, group_ranks, 5, leading_hand_category)
        if str_high is not None:
            return hrc_category_filtered(4, [str_high], 5, leading_hand_category)
        return hrc_category_filtered(0, group_ranks, 5, leading_hand_category)
    raise AssertionError(f"unreachable shape {shape}")


# Short deck poker

_WHEEL_SHORT_DECK = (9, frozenset((14, 9, 8, 7, 6)))
_STRAIGHT_SEQS_SHORT_DECK = tuple(
    (low + 4, frozenset(range(low, low + 5))) for low in range(10, 5, -1)
) + (_WHEEL_SHORT_DECK,)
_STRAIGHT_BY_MASK_SHORT_DECK = {
    rank_mask(ranks): high for high, ranks in _STRAIGHT_SEQS_SHORT_DECK
}


def ranking_short_deck(
    cards: tuple[int, int, int, int, int], leading_hand_category: int
) -> tuple[int, int]:
    """Rank a 5-card set under short deck rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    shape = tuple(cnt for cnt, _ in counts)
    group_ranks = [rank for _, rank in counts]

    if shape == (4, 1):
        return hrc_category_filtered(7, group_ranks, 5, leading_hand_category)
    if shape == (3, 2):
        return hrc_category_filtered(5, group_ranks, 5, leading_hand_category)
    if shape == (3, 1, 1):
        return hrc_category_filtered(3, group_ranks, 5, leading_hand_category)
    if shape == (2, 2, 1):
        return hrc_category_filtered(2, group_ranks, 5, leading_hand_category)
    if shape == (2, 1, 1, 1):
        return hrc_category_filtered(1, group_ranks, 5, leading_hand_category)
    if shape == (1, 1, 1, 1, 1):
        flush = is_flush(cards)
        str_high = straight_high(cards, _STRAIGHT_BY_MASK_SHORT_DECK)

        if flush and str_high is not None:
            return (hand_rank_code(8, [str_high], 5), 8)
        # Flushes are better than full houses in short deck
        if flush:
            return hrc_category_filtered(6, group_ranks, 5, leading_hand_category)
        if str_high is not None:
            if leading_hand_category > 4:
                return (0, 0)
            return hrc_category_filtered(4, [str_high], 5, leading_hand_category)
        return hrc_category_filtered(0, group_ranks, 5, leading_hand_category)
    raise AssertionError(f"unreachable shape {shape}")


# Ace to Five low


def ranking_ace_to_five_low(
    cards: tuple[int, int, int, int, int], leading_hand_category: int
) -> tuple[int, int]:
    """Rank a 5-card set under Ace to Five low rules."""
    if len(cards) != 5:
        raise ValueError(f"Invalid size: {cards!r} (expected 5 cards)")

    counts = rank_counts(cards)
    shape = tuple(cnt for cnt, _ in counts)
    # Aces are low - invert all other cards
    group_ranks = [(14 if rank == 14 else (14 - rank)) for _, rank in counts]

    if shape == (4, 1):
        return hrc_category_filtered(0, group_ranks, 5, leading_hand_category)
    if shape == (3, 2):
        return hrc_category_filtered(1, group_ranks, 5, leading_hand_category)
    if shape == (3, 1, 1):
        return hrc_category_filtered(2, group_ranks, 5, leading_hand_category)
    if shape == (2, 2, 1):
        return hrc_category_filtered(3, group_ranks, 5, leading_hand_category)
    if shape == (2, 1, 1, 1):
        return hrc_category_filtered(4, group_ranks, 5, leading_hand_category)
    if shape == (1, 1, 1, 1, 1):
        return (hand_rank_code(5, group_ranks, 5), 5)
    raise AssertionError(f"unreachable shape {shape}")


# Badugi


def legal_badugi(cards: tuple[int, ...]) -> bool:
    """Checks if a Badugi hand is legal (has no matching card ranks or suits)."""
    suits = [c & 0xF for c in cards]
    ranks = [c >> 4 for c in cards]
    return len(set(suits)) == len(suits) and len(set(ranks)) == len(ranks)


def ranking_badugi(
    cards: tuple[int, ...], leading_hand_category: int
) -> tuple[int, int]:
    """Ranks a hand based on Badugi rules. Assumes it's a legal hand, otherwise the code is nonsense."""
    ranks = sorted(14 if (card >> 4) == 14 else (14 - (card >> 4)) for card in cards)
    return (hand_rank_code(0, ranks, len(cards)), 0)


# Specific poker variant evaluation functions


def evaluate_standard(pool: tuple[int, ...]) -> int:
    """Best 5-card hand from an n-card pool (e.g. Texas Hold'em)."""
    subsets = combinations(sorted(pool), 5)
    return best_of_subsets(subsets, ranking_standard)


def evaluate_short_deck(pool: tuple[int, ...]) -> int:
    """Best 5-card hand from an n-card pool (e.g. short deck Texas Hold'em)."""
    subsets = combinations(sorted(pool), 5)
    return best_of_subsets(subsets, ranking_short_deck)


def evaluate_ace_to_five_low(pool: tuple[int, ...]) -> int:
    """Best ('worst') 5-card hand from an n-card pool (e.g. Razz)."""
    subsets = combinations(sorted(pool), 5)
    return best_of_subsets(subsets, ranking_ace_to_five_low)


def evaluate_badugi(hand: tuple[int, int, int, int]) -> int:
    """
    Badugi evaluation of four cards.

    Tries size 4 first (a full Badugi), then 3, 2, 1. More cards beats fewer.
    """
    for size in (4, 3, 2, 1):
        subsets = (
            subset for subset in combinations(hand, size) if legal_badugi(subset)
        )
        code: int | None = best_of_subsets(subsets, ranking_badugi, allow_none=True)
        if code is not None:
            return code
    raise AssertionError(f"no subset is legal in hand {hand!r}")
