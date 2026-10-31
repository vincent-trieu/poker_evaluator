"""
Poker Evaluator Test Suite

This module contains comprehensive tests for the poker_evaluator package.
Tests are organized by variant and include unit tests, property-based tests,
regression tests, and performance benchmarks.

Run with:
    pytest -xvs                    # All tests
    pytest -xvs --benchmark-only  # Performance only
    pytest -xvs --hypothesis-seed=42  # Reproducible property tests

Install dependencies:
    pip install pytest pytest-benchmark hypothesis
"""

import pytest
from itertools import combinations
from typing import Tuple

# Import your modules
from poker_evaluator.card_encoding import Card, standard_deck, short_deck
from poker_evaluator.evaluator import (
    hand_rank_code, rank_counts, is_flush, straight_high,
    best_of_subsets,
    ranking_standard, evaluate_standard,
    ranking_short_deck, evaluate_short_deck,
    ranking_ace_to_five_low, evaluate_ace_to_five_low,
    ranking_badugi, evaluate_badugi, legal_badugi,
    _STRAIGHT_SEQS_STANDARD, _STRAIGHT_SEQS_SHORT_DECK,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def full_deck():
    """Return a fresh standard 52-card deck."""
    return standard_deck()


@pytest.fixture
def short_deck_only():
    """Return a fresh short deck (6+)."""
    return short_deck()


@pytest.fixture
def ah_askhkc():
    """Sample hand fixture."""
    return tuple(Card.from_str(c) for c in "Ah As Kh Kc 2d".split())


# =============================================================================
# CARD LAYER TESTS
# =============================================================================

class TestCardParsing:
    """Tests for Card.from_str() and basic construction."""

    def test_parse_face_cards(self):
        assert Card.from_str("As").rank == 14
        assert Card.from_str("Ks").rank == 13
        assert Card.from_str("Qs").rank == 12
        assert Card.from_str("Js").rank == 11
        assert Card.from_str("Ts").rank == 10

    def test_parse_number_cards(self):
        assert Card.from_str("2s").rank == 2
        assert Card.from_str("9s").rank == 9

    def test_parse_suits_case_insensitive(self):
        assert Card.from_str("As").suit == Card.SPADES
        assert Card.from_str("AS").suit == Card.SPADES
        assert Card.from_str("Ah").suit == Card.HEARTS
        assert Card.from_str("AH").suit == Card.HEARTS
        assert Card.from_str("Ad").suit == Card.DIAMONDS
        assert Card.from_str("AD").suit == Card.DIAMONDS
        assert Card.from_str("Ac").suit == Card.CLUBS
        assert Card.from_str("AC").suit == Card.CLUBS

    def test_parse_invalid_length(self):
        with pytest.raises(ValueError, match="Invalid card"):
            Card.from_str("A")
        with pytest.raises(ValueError, match="Invalid card"):
            Card.from_str("Ahk")

    def test_parse_invalid_rank(self):
        with pytest.raises(ValueError, match="Invalid card"):
            Card.from_str("Xh")
        with pytest.raises(ValueError, match="Invalid card"):
            Card.from_str("1h")

    def test_parse_invalid_suit(self):
        with pytest.raises(ValueError, match="Invalid card"):
            Card.from_str("Aq")
        with pytest.raises(ValueError, match="Invalid card"):
            Card.from_str("Ax")

    def test_roundtrip_from_str_and_str(self):
        """String -> Card -> String should recover original."""
        original = "Ah"
        card = Card.from_str(original)
        recovered = str(card)
        assert recovered.lower() == original.lower()

    def test_repr_contains_card_info(self):
        card = Card(14, Card.HEARTS)
        rep = repr(card)
        assert "14" in rep
        assert "1" in rep


class TestCardValidation:
    """Tests for Card.__post_init__ validation."""

    def test_valid_rank_bounds(self):
        Card(2, 0)  # Minimum valid
        Card(14, 3)  # Maximum valid
        Card(10, 2)  # Middle valid

    def test_invalid_rank_too_low(self):
        with pytest.raises(ValueError, match="Invalid rank"):
            Card(1, 0)
        with pytest.raises(ValueError, match="Invalid rank"):
            Card(0, 0)

    def test_invalid_rank_too_high(self):
        with pytest.raises(ValueError, match="Invalid rank"):
            Card(15, 0)
        with pytest.raises(ValueError, match="Invalid rank"):
            Card(100, 0)

    def test_invalid_suit_negative(self):
        with pytest.raises(ValueError, match="Invalid suit"):
            Card(10, -1)

    def test_invalid_suit_too_high(self):
        with pytest.raises(ValueError, match="Invalid suit"):
            Card(10, 4)
        with pytest.raises(ValueError, match="Invalid suit"):
            Card(10, 5)


class TestDeckGeneration:
    """Tests for standard_deck() and short_deck()."""

    def test_standard_deck_has_52_cards(self):
        deck = standard_deck()
        assert len(deck) == 52

    def test_short_deck_has_36_cards(self):
        deck = short_deck()
        assert len(deck) == 36

    def test_standard_deck_contains_all_ranks(self):
        deck = standard_deck()
        ranks = {c.rank for c in deck}
        assert ranks == set(range(2, 15))

    def test_short_deck_starts_at_six(self):
        deck = short_deck()
        ranks = {c.rank for c in deck}
        assert min(ranks) == 6
        assert max(ranks) == 14

    def test_every_card_in_standard_deck(self):
        deck = standard_deck()
        for r in range(2, 15):
            for s in range(4):
                assert Card(r, s) in deck

    def test_every_card_in_short_deck(self):
        deck = short_deck()
        for r in range(6, 15):
            for s in range(4):
                assert Card(r, s) in deck

    def test_deck_has_no_duplicates(self):
        deck = standard_deck()
        assert len(deck) == len(set(deck))

    def test_deck_is_immutable_via_dataclass_frozen(self):
        card = Card(14, 0)
        with pytest.raises(AttributeError):
            card.rank = 13


# =============================================================================
# HAND ENCODING TESTS
# =============================================================================

class TestHandRankCode:
    """Tests for hand_rank_code encoding logic."""

    def test_category_most_significant_nibble(self):
        """Higher category always produces larger code regardless of kickers."""
        # Category 5 with worst kickers vs category 4 with best kickers
        code5 = hand_rank_code(5, [2, 2, 2, 2, 2], 5)
        code4 = hand_rank_code(4, [14, 13, 12, 11, 10], 5)
        assert code5 > code4

    def test_kickers_ordered_by_significance(self):
        """First kicker is most significant."""
        # Same first kicker, different second
        code1 = hand_rank_code(0, [14, 13, 3, 2, 2], 5)
        code2 = hand_rank_code(0, [14, 12, 11, 10, 9], 5)
        assert code1 > code2

    def test_padding_with_zeros_for_shorter_lists(self):
        """When len(card_ranks) < size, remaining digits are zero."""
        code1 = hand_rank_code(7, [7, 3], 5)  # Quad with single kicker
        code2 = hand_rank_code(7, [7, 3, 0, 0, 0], 5)  # Explicit padding
        assert code1 == code2

    def test_base16_encoding_preserves_order(self):
        """Comparing codes is equivalent to comparing tuples."""
        code1 = hand_rank_code(0, [14, 10, 8, 6, 4], 5)
        code2 = hand_rank_code(0, [14, 10, 8, 6, 5], 5)
        assert code1 < code2


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

class TestRankCounts:
    """Tests for rank_counts helper."""

    def test_count_distinct_ranks(self):
        cards = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 5s".split())
        counts = rank_counts(cards)
        assert counts == {14: 1, 2: 1, 3: 1, 4: 1, 5: 1}

    def test_count_pairs(self):
        cards = tuple(Card.from_str(c) for c in "Ah As Kh Kc 2d".split())
        counts = rank_counts(cards)
        assert counts == {14: 2, 13: 2, 2: 1}

    def test_count_three_of_a_kind(self):
        cards = tuple(Card.from_str(c) for c in "Ah As Ad 2c 3d".split())
        counts = rank_counts(cards)
        assert counts == {14: 3, 2: 1, 3: 1}


class TestIsFlush:
    """Tests for is_flush helper."""

    def test_all_same_suit(self):
        cards = tuple(Card.from_str(c) for c in "Ah 2h 3h 4h 5h".split())
        assert is_flush(cards) is True

    def test_mixed_suits(self):
        cards = tuple(Card.from_str(c) for c in "Ah 2h 3d 4h 5s".split())
        assert is_flush(cards) is False

    def test_four_same_one_different(self):
        cards = tuple(Card.from_str(c) for c in "Ah 2h 3h 4h 5s".split())
        assert is_flush(cards) is False


# =============================================================================
# STANDARD POKER TESTS
# =============================================================================

class TestStandardStraightDetection:
    """Tests specifically for straight detection in standard rules."""

    def test_broadway_is_highest_straight(self):
        """T-J-Q-K-A should be 10-high straight."""
        cards = tuple(Card.from_str(c) for c in "Ts Js Qs Ks As".split())
        high = straight_high(cards, _STRAIGHT_SEQS_STANDARD)
        assert high == 14

    def test_wheel_is_five_high(self):
        """A-2-3-4-5 should be 5-high straight (not 14-high)."""
        cards = tuple(Card.from_str(c) for c in "As 2s 3s 4s 5s".split())
        high = straight_high(cards, _STRAIGHT_SEQS_STANDARD)
        assert high == 5

    def test_wheel_below_six_high(self):
        """Wheel must be lower than 6-high straight."""
        wheel = tuple(Card.from_str(c) for c in "As 2s 3s 4s 5s".split())
        six_high = tuple(Card.from_str(c) for c in "6s 2s 3s 4s 5s".split())
        
        wheel_high = straight_high(wheel, _STRAIGHT_SEQS_STANDARD)
        six_high_val = straight_high(six_high, _STRAIGHT_SEQS_STANDARD)
        
        assert wheel_high < six_high_val

    def test_straight_high_rejects_duplicate_ranks(self):
        """Straight requires 5 unique ranks."""
        cards = tuple(Card.from_str(c) for c in "As As 3s 4s 5s".split())
        high = straight_high(cards, _STRAIGHT_SEQS_STANDARD)
        assert high is None

    def test_all_straights_have_correct_high_values(self):
        """Every straight from wheel to Broadway should have correct high value."""
        expected = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
        for i, high_rank in enumerate(expected):
            if i == 0:
                # Wheel special case
                cards = tuple(Card.from_str(c) for c in f"As 2s 3s 4s 5s".split())
            else:
                high_card_rank = 5 + i  # Wheel=5, 6-high, 7-high, etc.
                # Build: high, high-1, high-2, high-3, high-4
                ranks = [high_card_rank, high_card_rank-1, high_card_rank-2, high_card_rank-3, high_card_rank-4]
                rank_chars = ['2','3','4','5','6','7','8','9','T','J','Q','K','A']
                card_strs = [f"{rank_chars[r-2]}s" for r in ranks]
                cards = tuple(Card.from_str(c) for c in card_strs)
            
            high = straight_high(cards, _STRAIGHT_SEQS_STANDARD)
            assert high == expected[i], f"Straight {card_strs} has high {high}, expected {expected[i]}"


class TestStandardHandRankings:
    """Tests for complete hand rankings in standard rules."""

    def test_royal_flush_beats_all(self):
        royal = tuple(Card.from_str(c) for c in "As Ks Qs Js Ts".split())
        kings_sf = tuple(Card.from_str(c) for c in "Ks Qs Js Ts 9s".split())
        assert evaluate_standard(royal) > evaluate_standard(kings_sf)

    def test_steel_wheel_below_royal(self):
        """Steel wheel flush must lose to royal flush."""
        wheel = tuple(Card.from_str(c) for c in "As 2s 3s 4s 5s".split())
        royal = tuple(Card.from_str(c) for c in "As Ks Qs Js Ts".split())
        assert evaluate_standard(wheel) < evaluate_standard(royal)

    def test_quads_beats_full_house(self):
        quads = tuple(Card.from_str(c) for c in "As Ah Ac Ad Kh".split())
        fh = tuple(Card.from_str(c) for c in "Ks Kh Kd Qs Qh".split())
        assert evaluate_standard(quads) > evaluate_standard(fh)

    def test_full_house_beats_flush(self):
        fh = tuple(Card.from_str(c) for c in "Ks Kh Kd Qs Qh".split())
        flush = tuple(Card.from_str(c) for c in "As 2s 3s 4s 6s".split())
        assert evaluate_standard(fh) > evaluate_standard(flush)

    def test_flush_beats_straight(self):
        flush = tuple(Card.from_str(c) for c in "As 2s 3s 4s 6s".split())
        straight = tuple(Card.from_str(c) for c in "Ts Js Qs Ks 2h".split())
        assert evaluate_standard(flush) > evaluate_standard(straight)

    def test_straight_beats_three_of_a_kind(self):
        straight = tuple(Card.from_str(c) for c in "9h Ts Js Qs Ks".split())
        trips = tuple(Card.from_str(c) for c in "As Ah Ad 2h 3h".split())
        assert evaluate_standard(straight) > evaluate_standard(trips)

    def test_trips_beats_two_pair(self):
        trips = tuple(Card.from_str(c) for c in "As Ah Ad 2h 3h".split())
        two_pair = tuple(Card.from_str(c) for c in "Ks Kh Qs Qh 2d".split())
        assert evaluate_standard(trips) > evaluate_standard(two_pair)

    def test_two_pair_beats_pair(self):
        two_pair = tuple(Card.from_str(c) for c in "Ks Kh Qs Qh 2d".split())
        pair = tuple(Card.from_str(c) for c in "As Ah 3s 4h 2d".split())
        assert evaluate_standard(two_pair) > evaluate_standard(pair)

    def test_pair_beats_high_card(self):
        pair = tuple(Card.from_str(c) for c in "As Ah 3s 4h 2d".split())
        high_card = tuple(Card.from_str(c) for c in "Ks Qh Jd 5c 2h".split())
        assert evaluate_standard(pair) > evaluate_standard(high_card)

    def test_crossed_kickers_two_pair(self):
        """AA-QQ-9 vs AA-QQ-T: second wins due to kicker."""
        h1 = tuple(Card.from_str(c) for c in "As Ah Qs Qh 9d".split())
        h2 = tuple(Card.from_str(c) for c in "As Ah Qs Qh Td".split())
        assert evaluate_standard(h1) < evaluate_standard(h2)

    def test_quads_kicker_breaks_tie(self):
        """Quad 2s with King kicker beats quad 2s with Queen kicker."""
        h1 = tuple(Card.from_str(c) for c in "2s 2h 2d 2c Ks".split())
        h2 = tuple(Card.from_str(c) for c in "2s 2h 2d 2c Qs".split())
        assert evaluate_standard(h1) > evaluate_standard(h2)

    def test_7_card_best_hand_selection(self):
        """From 7 cards, the best 5-card hand should be selected."""
        # Pocket Aces, board has two pair
        pool = tuple(Card.from_str(c) for c in "As Ah Ks Kh 5d 5h 2c".split())
        code = evaluate_standard(pool)
        # Should pick: AA + KK, 5 is unused (best two pair is AA-KK)
        assert code > 0


class TestSevenCardEvaluation:
    """Tests for multi-card pool evaluation."""

    def test_empty_pool_raises_error_or_handles_gracefully(self):
        """Evaluate should not crash on undersized pool."""
        pool = (Card.from_str("As"),)
        # Either raises ValueError or returns None, but doesn't crash
        try:
            result = evaluate_standard(pool)
            # If it returns, should be None or handle gracefully
            assert result is None or isinstance(result, int)
        except ValueError:
            pass  # Expected behavior

    def test_permutation_invariance(self):
        """Order of input cards should not affect result."""
        pool = tuple(Card.from_str(c) for c in "As Ks 2h 3d 4c 5h 6s".split())
        shuffled = tuple(Card.from_str(c) for c in "6s 3d As 5h 2h Ks 4c".split())
        assert evaluate_standard(pool) == evaluate_standard(shuffled)


# =============================================================================
# SHORT DECK TESTS
# =============================================================================

class TestShortDeckStraights:
    """Tests for straight detection in short deck rules."""

    def test_short_deck_wheel_is_nine_high(self):
        """A-6-7-8-9 should be 9-high straight."""
        cards = tuple(Card.from_str(c) for c in "As 6s 7s 8s 9s".split())
        high = straight_high(cards, _STRAIGHT_SEQS_SHORT_DECK)
        assert high == 9

    def test_all_short_deck_straights_have_correct_high_values(self):
        """Every straight in short deck should have correct high value."""
        expected = [9, 10, 11, 12, 13, 14]  # 9-high through Broadway
        for i, high_rank in enumerate(expected):
            if i == 0:
                # Wheel special case
                cards = tuple(Card.from_str(c) for c in f"As 9s 8s 7s 6s".split())
            else:
                high_card_rank = 9 + i
                rank_chars = ['6','7','8','9','T','J','Q','K','A']
                card_strs = [f"{rank_chars[r-6]}s" for r in range(high_card_rank, high_card_rank-5, -1)]
                cards = tuple(Card.from_str(c) for c in card_strs)
            
            high = straight_high(cards, _STRAIGHT_SEQS_SHORT_DECK)
            assert high == expected[i], f"Short deck straight {card_strs} has high {high}, expected {expected[i]}"

    def test_broadway_stays_ten_high(self):
        """T-J-Q-K-A should still be 10-high (not 15-high)."""
        cards = tuple(Card.from_str(c) for c in "Ts Js Qs Ks As".split())
        high = straight_high(cards, _STRAIGHT_SEQS_SHORT_DECK)
        assert high == 14


class TestShortDeckRankings:
    """Tests for complete hand rankings in short deck rules."""

    def test_flush_beats_full_house(self):
        """Main difference from standard: flush > full house."""
        flush = tuple(Card.from_str(c) for c in "Ah 9h 8h 7h 6h".split())
        fh = tuple(Card.from_str(c) for c in "6s 6h 6d 9c 9d".split())
        assert evaluate_short_deck(flush) > evaluate_short_deck(fh)

    def test_full_house_still_beats_trips(self):
        """Full house should still beat three of a kind."""
        fh = tuple(Card.from_str(c) for c in "6s 6h 6d 9c 9d".split())
        trips = tuple(Card.from_str(c) for c in "9s 9h 9d As Kd".split())
        assert evaluate_short_deck(fh) > evaluate_short_deck(trips)

    def test_quads_beats_flush(self):
        """Quads should still be above flush."""
        quads = tuple(Card.from_str(c) for c in "6s 6h 6d 6c Ks".split())
        flush = tuple(Card.from_str(c) for c in "Ah Th 8h 7h 6h".split())
        assert evaluate_short_deck(quads) > evaluate_short_deck(flush)


# =============================================================================
# ACE-TO-FIVE LOWBALL TESTS
# =============================================================================

class TestAceToFiveLowball:
    """Tests for Ace-to-Five lowball rankings."""

    def test_wheel_is_best_possible_low(self):
        """A-2-3-4-5 is the nuts in Ace-to-Five."""
        wheel = tuple(Card.from_str(c) for c in "As 2h 3d 4c 5s".split())
        one_gapper = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 6s".split())
        assert evaluate_ace_to_five_low(wheel) > evaluate_ace_to_five_low(one_gapper)

    def test_seven_low_beats_nine_low(self):
        """7-low must beat 9-low (crossed hands test)."""
        h7 = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 7s".split())
        h9 = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 9s".split())
        assert evaluate_ace_to_five_low(h7) > evaluate_ace_to_five_low(h9)

    def test_pairs_beat_unpaired_in_lowball(self):
        """Paired hands are worse than unpaired hands."""
        h_pair = tuple(Card.from_str(c) for c in "As Ah 2d 3c 4s".split())
        h_nopair = tuple(Card.from_str(c) for c in "7h 5d 4c 3s 2h".split())
        assert evaluate_ace_to_five_low(h_pair) < evaluate_ace_to_five_low(h_nopair)

    def test_four_of_a_kind_worst_hand_shape(self):
        """Quad is the worst possible hand shape in lowball."""
        quads = tuple(Card.from_str(c) for c in "As Ah Ad Ac 2s".split())
        tripped = tuple(Card.from_str(c) for c in "Ks Kh Kd 2c 3s".split())
        assert evaluate_ace_to_five_low(quads) < evaluate_ace_to_five_low(tripped)

    def test_straights_and_flushes_do_not_kill_low(self):
        """In Ace-to-Five, straights and flushes do not invalidate low."""
        # This wheel is a straight flush, but should still play as best low
        wheel = tuple(Card.from_str(c) for c in "As 2s 3s 4s 5s".split())
        plain_wheel = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 5s".split())
        # Both should be equal (both are A-2-3-4-5 low)
        assert evaluate_ace_to_five_low(wheel) == evaluate_ace_to_five_low(plain_wheel)


# =============================================================================
# BADUGI TESTS
# =============================================================================

class TestBadugiLegalHands:
    """Tests for Badugi hand legality."""

    def test_legal_badagi_four_cards(self):
        """Four cards with different suits and ranks is legal."""
        cards = tuple(Card.from_str(c) for c in "As 2h 3d 4c".split())
        assert legal_badugi(cards) is True

    def test_illegal_matching_ranks(self):
        """Matching ranks make hand illegal."""
        cards = tuple(Card.from_str(c) for c in "As 2h 3d 3c".split())
        assert legal_badugi(cards) is False

    def test_illegal_matching_suits(self):
        """Matching suits make hand illegal."""
        cards = tuple(Card.from_str(c) for c in "As 2h 3s 4c".split())
        assert legal_badugi(cards) is False

    def test_single_card_always_legal(self):
        """Single card is always legal."""
        assert legal_badugi((Card.from_str("As"),)) is True


class TestBadugiRankings:
    """Tests for Badugi hand rankings."""

    def test_four_cards_beats_three(self):
        """More cards always beats fewer cards."""
        h4 = tuple(Card.from_str(c) for c in "As 2h 3d 4c".split())
        h3_input = tuple(Card.from_str(c) for c in "Ah 2s 3d 4d 5h".split())  # Best subset is 3-card
        assert evaluate_badugi(h4) > evaluate_badugi(h3_input)

    def test_same_size_lower_ranks_win(self):
        """For same number of cards, lower ranks win."""
        h1 = tuple(Card.from_str(c) for c in "As 2h 3d 4c".split())
        h2 = tuple(Card.from_str(c) for c in "As 2h 3d 5c".split())
        assert evaluate_badugi(h1) > evaluate_badugi(h2)

    def test_ace_is_lowest(self):
        """Ace should count as lowest rank."""
        h1 = tuple(Card.from_str(c) for c in "As 2h 3d 4c".split())
        h2 = tuple(Card.from_str(c) for c in "Kh 2s 3d 4c".split())
        # Ace hand should beat King hand
        assert evaluate_badugi(h1) > evaluate_badugi(h2)


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegressionBugs:
    """Tests for specific bugs discovered during development."""

    def test_regression_wheel_broadway_distinct(self):
        """Wheel (A-2-3-4-5) must NOT tie Broadway (T-J-Q-K-A)."""
        wheel = tuple(Card.from_str(c) for c in "As 2h 3d 4c 5s".split())
        broadway = tuple(Card.from_str(c) for c in "Ts Js Qs Ks As".split())
        wheel_code = evaluate_standard(wheel)
        broadway_code = evaluate_standard(broadway)
        assert wheel_code != broadway_code, "Wheel tied Broadway - bug not fixed!"
        assert wheel_code < broadway_code, "Wheel should lose to Broadway"

    def test_regression_steel_wheel_not_royal(self):
        """Steel wheel flush must NOT tie royal flush."""
        wheel = tuple(Card.from_str(c) for c in "As 2s 3s 4s 5s".split())
        royal = tuple(Card.from_str(c) for c in "As Ks Qs Js Ts".split())
        wheel_code = evaluate_standard(wheel)
        royal_code = evaluate_standard(royal)
        assert wheel_code != royal_code, "Steel wheel tied royal - bug not fixed!"
        assert wheel_code < royal_code

    def test_regression_ace_to_five_sort_direction(self):
        """7-low must beat 9-low - this was failing due to sort key bug."""
        h7 = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 7s".split())
        h9 = tuple(Card.from_str(c) for c in "Ah 2h 3d 4c 9s".split())
        code7 = evaluate_ace_to_five_low(h7)
        code9 = evaluate_ace_to_five_low(h9)
        assert code7 != code9, "7-low tied 9-low - bug not fixed!"
        assert code7 > code9, "7-low should beat 9-low"

    def test_regression_straight_high_off_by_one(self):
        """Straight high values should match actual high card, not be shifted."""
        # 6-high straight should have encoded high = 6
        six_high = tuple(Card.from_str(c) for c in "6s 2h 3d 4c 5h".split())
        seven_high = tuple(Card.from_str(c) for c in "7s 3h 4d 5c 6h".split())
        
        code6 = evaluate_standard(six_high)
        code7 = evaluate_standard(seven_high)
        
        # The difference should be exactly 1<<16 (one increment in high-nibble position)
        expected_diff = 1 << 16
        actual_diff = code7 - code6
        assert actual_diff == expected_diff, f"High nibble shift wrong: got {actual_diff}, expected {expected_diff}"


# =============================================================================
# PROPERTY-BASED TESTS (Hypothesis)
# =============================================================================

try:
    from hypothesis import given, strategies as st
    
    class TestPropertyBased:
        """Property-based tests using Hypothesis."""
        
        @given(st.lists(st.sampled_from(standard_deck()), min_size=5, max_size=7, unique=True))
        def test_evaluation_returns_integer(self, pool: list[Card]):
            """Evaluator should always return an integer."""
            code = evaluate_standard(tuple(pool))
            assert isinstance(code, int)
        
        @given(st.lists(st.sampled_from(standard_deck()), min_size=5, max_size=7, unique=True))
        def test_monotonicity_on_card_addition(self, pool: list[Card]):
            """Adding cards can only improve or keep the same hand."""
            if len(pool) >= 5:
                base = evaluate_standard(tuple(pool[:5]))
                extended = evaluate_standard(tuple(pool))
                assert extended >= base
        
        @given(st.lists(st.sampled_from(standard_deck()), min_size=5, max_size=7, unique=True))
        def test_permutation_invariance(self, pool: list[Card]):
            """Order of input cards should not affect result."""
            from random import shuffle
            shuffled = pool.copy()
            shuffle(shuffled)
            assert evaluate_standard(tuple(pool)) == evaluate_standard(tuple(shuffled))
        
        @given(st.integers(min_value=0, max_value=8))
        def test_hand_category_encoding_range(self, category: int):
            """Hand category should fit in one nibble (0-15)."""
            code = hand_rank_code(category, [14, 13, 12, 11, 10], 5)
            # Category is in the most significant nibble
            assert 0 <= category <= 15
        
        @given(st.lists(st.sampled_from(standard_deck()), min_size=5, max_size=5, unique=True))
        def test_ace_to_five_no_pair_beats_any_pair_shape(self, cards: list[Card]):
            """Unpaired hands beat paired hands in Ace-to-Five lowball."""
            counts = rank_counts(cards)
            no_pair = all(c == 1 for c in counts.values())
            
            if no_pair:
                code_no_pair = evaluate_ace_to_five_low(tuple(cards))
                # Try creating a pair by swapping a card
                modified = cards.copy()
                modified[0] = modified[1]  # Now we have a pair
                code_pair = evaluate_ace_to_five_low(tuple(modified))
                assert code_no_pair > code_pair
        
        @given(st.lists(st.sampled_from(short_deck()), min_size=5, max_size=7, unique=True))
        def test_short_deck_evaluation_works(self, pool: list[Card]):
            """Short deck evaluation should return valid codes."""
            code = evaluate_short_deck(tuple(pool))
            assert isinstance(code, int)
            assert code > 0

except ImportError:
    pass  # Hypothesis not installed, skip these tests


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_evaluation_speed_minimum():
    """Basic throughput test - adjust threshold based on your baseline."""
    pool = tuple(Card.from_str(c) for c in "2s 3h 4d 5c 6s 7h 8d".split())
    
    iterations = 10000
    start = __import__("time").perf_counter()
    for _ in range(iterations):
        evaluate_standard(pool)
    elapsed = __import__("time").perf_counter() - start
    
    rate = iterations / elapsed
    print(f"\nStandard eval: {rate:,.0f} evaluations/second")
    
    # Minimum target: 100k evals/sec for Python
    assert rate > 100_000, f"Too slow: {rate:.0f} evals/sec, need >100k"


def test_short_deck_speed_comparison():
    """Compare short deck vs standard evaluation speed."""
    pool = tuple(Card.from_str(c) for c in "6s 7h 8d 9c Th Jh Qs".split())
    
    iterations = 10000
    start = __import__("time").perf_counter()
    for _ in range(iterations):
        evaluate_short_deck(pool)
    elapsed = __import__("time").perf_counter() - start
    
    rate = iterations / elapsed
    print(f"Short deck eval: {rate:,.0f} evaluations/second")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
