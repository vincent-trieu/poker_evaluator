"""
poker_evaluator/evaluator.py

This evaluator works by taking a pool of cards and working out what the best hand is
that can be constructed from them. This hand is not necessarily five cards.

This allows a level of flexibility that allows the evaluator to work with games
like Badugi, which don't use the standard 5-card hand rankings.
"""

def hand_rank_code(hand_type: int, card_ranks: tuple[int, ...], size: int):
    """
    Function that returns an encoding of a hand and its ranking, as a comparable int.

    Type represents what kind of hand it is e.g. flush, straight, and how good it is in the poker variant.
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
    code = hand_type
    for i in range(size):
        code = (code << 4) + (card_ranks[i] if i < len(card_ranks) else 0)
    return code
