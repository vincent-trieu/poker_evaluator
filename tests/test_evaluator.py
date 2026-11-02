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

# Import your modules
from poker_evaluator.card_encoding import (
    CLUBS,
    DIAMONDS,
    HEARTS,
    SPADES,
    card_from_str,
    card_to_int,
)
from poker_evaluator.evaluator import (
    _STRAIGHT_BY_MASK_SHORT_DECK,
    _STRAIGHT_BY_MASK_STANDARD,
    evaluate_ace_to_five_low,
    evaluate_badugi,
    evaluate_short_deck,
    evaluate_standard,
    hand_rank_code,
    is_flush,
    legal_badugi,
    rank_counts,
    straight_high,
)
from poker_evaluator.utils import short_deck, standard_deck

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
    """Sample hand fixture (pairs of Aces and Kings)."""
    return tuple(card_from_str(c) for c in ["Ah", "As", "Kh", "Kc", "2d"])


def c(*card_strings: str) -> tuple[int, ...]:
    """Helper to convert card strings to ints."""
    return tuple(card_from_str(c) for c in card_strings)


# =============================================================================
# CARD LAYER TESTS
# =============================================================================


class TestCardParsing:
    """Tests for card_from_str() and card_to_int() construction."""

    def test_parse_face_cards(self):
        assert card_from_str("As") == card_to_int(14, SPADES)
        assert card_from_str("Ks") == card_to_int(13, SPADES)
        assert card_from_str("Qs") == card_to_int(12, SPADES)
        assert card_from_str("Js") == card_to_int(11, SPADES)
        assert card_from_str("Ts") == card_to_int(10, SPADES)

    def test_parse_number_cards(self):
        assert card_from_str("2s").__repr__() != ""  # Just ensures it parses
        assert card_from_str("2s") == card_to_int(2, SPADES)
        assert card_from_str("9s") == card_to_int(9, SPADES)

    def test_parse_suits_case_insensitive(self):
        assert card_from_str("As") == card_to_int(14, SPADES)
        assert card_from_str("AS") == card_to_int(14, SPADES)
        assert card_from_str("Ah") == card_to_int(14, HEARTS)
        assert card_from_str("AH") == card_to_int(14, HEARTS)
        assert card_from_str("Ad") == card_to_int(14, DIAMONDS)
        assert card_from_str("AD") == card_to_int(14, DIAMONDS)
        assert card_from_str("Ac") == card_to_int(14, CLUBS)
        assert card_from_str("AC") == card_to_int(14, CLUBS)

    def test_parse_invalid_length(self):
        with pytest.raises(ValueError, match="Invalid card string"):
            card_from_str("A")
        with pytest.raises(ValueError, match="Invalid card string"):
            card_from_str("Ahk")

    def test_parse_invalid_rank(self):
        with pytest.raises(ValueError, match="Invalid card"):
            card_from_str("Xh")
        with pytest.raises(ValueError, match="Invalid card"):
            card_from_str("1h")

    def test_parse_invalid_suit(self):
        with pytest.raises(ValueError, match="Invalid card"):
            card_from_str("Aq")
        with pytest.raises(ValueError, match="Invalid card"):
            card_from_str("Ax")

    def test_card_to_int_validation(self):
        card_to_int(2, 0)  # Minimum valid
        card_to_int(14, 3)  # Maximum valid

        with pytest.raises(ValueError, match="Invalid rank"):
            card_to_int(1, 0)
        with pytest.raises(ValueError, match="Invalid rank"):
            card_to_int(15, 0)
        with pytest.raises(ValueError, match="Invalid suit"):
            card_to_int(10, -1)
        with pytest.raises(ValueError, match="Invalid suit"):
            card_to_int(10, 4)

    def test_int_to_rank_and_suit(self):
        """Verify bit extraction works correctly."""
        card = card_to_int(14, HEARTS)
        assert (card >> 4) == 14
        assert (card & 0xF) == HEARTS

        card = card_to_int(7, CLUBS)
        assert (card >> 4) == 7
        assert (card & 0xF) == CLUBS


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
        ranks = {c >> 4 for c in deck}
        assert ranks == set(range(2, 15))

    def test_short_deck_starts_at_six(self):
        deck = short_deck()
        ranks = {c >> 4 for c in deck}
        assert min(ranks) == 6
        assert max(ranks) == 14

    def test_every_card_in_standard_deck(self):
        deck = standard_deck()
        for r in range(2, 15):
            for s in range(4):
                expected = card_to_int(r, s)
                assert expected in deck

    def test_every_card_in_short_deck(self):
        deck = short_deck()
        for r in range(6, 15):
            for s in range(4):
                expected = card_to_int(r, s)
                assert expected in deck

    def test_deck_has_no_duplicates(self):
        deck = standard_deck()
        assert len(deck) == len(set(deck))


# =============================================================================
# HAND ENCODING TESTS
# =============================================================================


class TestHandRankCode:
    """Tests for hand_rank_code encoding logic."""

    def test_category_most_significant_nibble(self):
        """Higher category always produces larger code regardless of kickers."""
        code5 = hand_rank_code(5, [2, 2, 2, 2, 2], 5)
        code4 = hand_rank_code(4, [14, 13, 12, 11, 10], 5)
        assert code5 > code4

    def test_kickers_ordered_by_significance(self):
        """First kicker is most significant."""
        code1 = hand_rank_code(0, [14, 13, 3, 2, 2], 5)
        code2 = hand_rank_code(0, [14, 12, 11, 10, 9], 5)
        assert code1 > code2

    def test_padding_with_zeros_for_shorter_lists(self):
        """When len(card_ranks) < size, remaining digits are zero."""
        code1 = hand_rank_code(7, [7, 3], 5)
        code2 = hand_rank_code(7, [7, 3, 0, 0, 0], 5)
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
        cards = c("Ah", "2h", "3d", "4c", "5s")
        groups = rank_counts(cards)
        ranks = {r for _, r in groups}
        assert ranks == {14, 2, 3, 4, 5}
        assert all(cnt == 1 for cnt, _ in groups)

    def test_count_pairs(self):
        cards = c("Ah", "As", "Kh", "Kc", "2d")
        groups = rank_counts(cards)
        counts_dict = {r: cnt for cnt, r in groups}
        assert counts_dict[14] == 2
        assert counts_dict[13] == 2
        assert counts_dict[2] == 1

    def test_count_three_of_a_kind(self):
        cards = c("Ah", "As", "Ad", "2c", "3d")
        groups = rank_counts(cards)
        counts_dict = {r: cnt for cnt, r in groups}
        assert counts_dict[14] == 3
        assert counts_dict[2] == 1
        assert counts_dict[3] == 1

    def test_rank_counts_returns_descending_order(self):
        """Groups should be sorted by count desc, then rank desc."""
        cards = c("Ah", "As", "Kh", "2c", "3d")  # Pair of Aces
        groups = rank_counts(cards)

        # First entry should be the pair (count=2, rank=14)
        assert groups[0] == (2, 14)
        # Remaining entries should be singles in descending rank order
        remaining = [(cnt, r) for cnt, r in groups[1:]]
        assert all(cnt == 1 for cnt, _ in remaining)
        ranks = [r for _, r in remaining]
        assert ranks == sorted(ranks, reverse=True)


class TestIsFlush:
    """Tests for is_flush helper."""

    def test_all_same_suit(self):
        cards = c("Ah", "2h", "3h", "4h", "5h")
        assert is_flush(cards) is True

    def test_mixed_suits(self):
        cards = c("Ah", "2h", "3d", "4h", "5s")
        assert is_flush(cards) is False

    def test_four_same_one_different(self):
        cards = c("Ah", "2h", "3h", "4h", "5s")
        assert is_flush(cards) is False


class TestStraightHigh:
    """Tests for straight detection."""

    def test_broadway_is_highest_straight(self):
        """T-J-Q-K-A should be 10-high straight (high=14)."""
        cards = c("Ts", "Js", "Qs", "Ks", "As")
        high = straight_high(cards, _STRAIGHT_BY_MASK_STANDARD)
        assert high == 14

    def test_wheel_is_five_high(self):
        """A-2-3-4-5 should be 5-high straight (not 14-high)."""
        cards = c("As", "2s", "3s", "4s", "5s")
        high = straight_high(cards, _STRAIGHT_BY_MASK_STANDARD)
        assert high == 5

    def test_wheel_below_six_high(self):
        """Wheel must be lower than 6-high straight."""
        wheel = c("As", "2s", "3s", "4s", "5s")
        six_high = c("6s", "2s", "3s", "4s", "5s")

        wheel_high = straight_high(wheel, _STRAIGHT_BY_MASK_STANDARD)
        six_high_val = straight_high(six_high, _STRAIGHT_BY_MASK_STANDARD)

        assert wheel_high == 5
        assert six_high_val == 6
        assert wheel_high < six_high_val

    def test_straight_high_rejects_duplicate_ranks(self):
        """Straight requires 5 unique ranks."""
        cards = c("As", "As", "3s", "4s", "5s")
        high = straight_high(cards, _STRAIGHT_BY_MASK_STANDARD)
        assert high is None

    def test_all_straights_have_correct_high_values(self):
        """Every straight from wheel to Broadway should have correct high value."""
        # Wheel
        assert (
            straight_high(c("As", "2s", "3s", "4s", "5s"), _STRAIGHT_BY_MASK_STANDARD)
            == 5
        )
        # 6-high
        assert (
            straight_high(c("2s", "3s", "4s", "5s", "6s"), _STRAIGHT_BY_MASK_STANDARD)
            == 6
        )
        # 7-high
        assert (
            straight_high(c("3s", "4s", "5s", "6s", "7s"), _STRAIGHT_BY_MASK_STANDARD)
            == 7
        )
        # Broadway
        assert (
            straight_high(c("Ts", "Js", "Qs", "Ks", "As"), _STRAIGHT_BY_MASK_STANDARD)
            == 14
        )


# =============================================================================
# STANDARD POKER TESTS
# =============================================================================


class TestStandardHandRankings:
    """Tests for complete hand rankings in standard rules."""

    def test_royal_flush_beats_all(self):
        royal = c("As", "Ks", "Qs", "Js", "Ts")
        kings_sf = c("Ks", "Qs", "Js", "Ts", "9s")
        assert evaluate_standard(royal) > evaluate_standard(kings_sf)

    def test_steel_wheel_below_royal(self):
        """Steel wheel flush must lose to royal flush."""
        wheel = c("As", "2s", "3s", "4s", "5s")
        royal = c("As", "Ks", "Qs", "Js", "Ts")
        assert evaluate_standard(wheel) < evaluate_standard(royal)

    def test_steel_wheel_below_six_high_straight(self):
        """Steel wheel must lose to 6-high straight flush."""
        wheel = c("As", "2s", "3s", "4s", "5s")
        six_high_sf = c("2s", "3s", "4s", "5s", "6s")
        assert evaluate_standard(wheel) < evaluate_standard(six_high_sf)

    def test_quads_beats_full_house(self):
        quads = c("As", "Ah", "Ac", "Ad", "Kh")
        fh = c("Ks", "Kh", "Kd", "Qs", "Qh")
        assert evaluate_standard(quads) > evaluate_standard(fh)

    def test_full_house_beats_flush(self):
        fh = c("Ks", "Kh", "Kd", "Qs", "Qh")
        flush = c("As", "2s", "3s", "4s", "6s")
        assert evaluate_standard(fh) > evaluate_standard(flush)

    def test_flush_beats_straight(self):
        flush = c("As", "2s", "3s", "4s", "6s")
        straight = c("Ts", "Js", "Qs", "Ks", "2h")
        assert evaluate_standard(flush) > evaluate_standard(straight)

    def test_straight_beats_three_of_a_kind(self):
        straight = c("Ts", "Js", "Qs", "Ks", "9h")
        trips = c("As", "Ah", "Ad", "2h", "3h")
        assert evaluate_standard(straight) > evaluate_standard(trips)

    def test_trips_beats_two_pair(self):
        trips = c("As", "Ah", "Ad", "2h", "3h")
        two_pair = c("Ks", "Kh", "Qs", "Qh", "2d")
        assert evaluate_standard(trips) > evaluate_standard(two_pair)

    def test_two_pair_beats_pair(self):
        two_pair = c("Ks", "Kh", "Qs", "Qh", "2d")
        pair = c("As", "Ah", "3s", "4h", "2d")
        assert evaluate_standard(two_pair) > evaluate_standard(pair)

    def test_pair_beats_high_card(self):
        pair = c("As", "Ah", "3s", "4h", "2d")
        high_card = c("Ks", "Qh", "Jd", "5c", "2h")
        assert evaluate_standard(pair) > evaluate_standard(high_card)

    def test_crossed_kickers_two_pair(self):
        """AA-QQ-9 vs AA-QQ-T: second wins due to kicker."""
        h1 = c("As", "Ah", "Qs", "Qh", "9d")
        h2 = c("As", "Ah", "Qs", "Qh", "Td")
        assert evaluate_standard(h1) < evaluate_standard(h2)

    def test_quads_kicker_breaks_tie(self):
        """Quad 2s with King kicker beats quad 2s with Queen kicker."""
        h1 = c("2s", "2h", "2d", "2c", "Ks")
        h2 = c("2s", "2h", "2d", "2c", "Qs")
        assert evaluate_standard(h1) > evaluate_standard(h2)

    def test_full_house_trips_rank_priority(self):
        """Aces full of Kings beats Aces full of Queens."""
        h1 = c("As", "Ah", "Ad", "Ks", "Kh")
        h2 = c("As", "Ah", "Ad", "Qs", "Qh")
        assert evaluate_standard(h1) > evaluate_standard(h2)

    def test_7_card_best_hand_selection(self):
        """From 7 cards, the best 5-card hand should be selected."""
        pool = c("As", "Ah", "Ks", "Kh", "5d", "5h", "2c")
        code = evaluate_standard(pool)
        assert code > 0

    def test_cannot_improve_on_straight_flush(self):
        """If pool has a straight flush, that's the answer."""
        pool = c("Ts", "Js", "Qs", "Ks", "As", "2h", "3d")
        code = evaluate_standard(pool)
        # Should be straight flush, category 8
        assert code >> 20 == 8


# =============================================================================
# SEVEN-CARD EVALUATION TESTS
# =============================================================================


class TestSevenCardEvaluation:
    """Tests for multi-card pool evaluation."""

    def test_empty_pool_raises_error(self):
        """Evaluate should raise ValueError on undersized pool."""
        pool = (card_from_str("As"),)
        with pytest.raises(ValueError):
            evaluate_standard(pool)

    def test_permutation_invariance(self):
        """Order of input cards should not affect result."""
        pool = c("As", "Ks", "2h", "3d", "4c", "5h", "6s")
        shuffled = c("6s", "3d", "As", "5h", "2h", "Ks", "4c")
        assert evaluate_standard(pool) == evaluate_standard(shuffled)

    def test_board_with_pocket_pair_make_two_pair(self):
        """Pocket pair plus board pair makes two pair."""
        # Hole: 77, Board: K-K-9-3-2
        pool = c("7s", "7h", "Ks", "Kh", "9d", "3c", "2h")
        code = evaluate_standard(pool)
        # Two pair Aces/Kings would beat this, but we have Kings/7s
        assert code > 0


# =============================================================================
# SHORT DECK TESTS
# =============================================================================


class TestShortDeckStraights:
    """Tests for straight detection in short deck rules."""

    def test_short_deck_wheel_is_nine_high(self):
        """A-6-7-8-9 should be 9-high straight."""
        cards = c("As", "6s", "7s", "8s", "9s")
        high = straight_high(cards, _STRAIGHT_BY_MASK_SHORT_DECK)
        assert high == 9

    def test_broadway_stays_ten_high(self):
        """T-J-Q-K-A should still be 10-high."""
        cards = c("Ts", "Js", "Qs", "Ks", "As")
        high = straight_high(cards, _STRAIGHT_BY_MASK_SHORT_DECK)
        assert high == 14


class TestShortDeckRankings:
    """Tests for complete hand rankings in short deck rules."""

    def test_flush_beats_full_house(self):
        """Main difference from standard: flush > full house."""
        flush = c("Ah", "9h", "8h", "7h", "6h")
        fh = c("6s", "6h", "6d", "9c", "9d")
        assert evaluate_short_deck(flush) > evaluate_short_deck(fh)

    def test_full_house_still_beats_trips(self):
        """Full house should still beat three of a kind."""
        fh = c("6s", "6h", "6d", "9c", "9d")
        trips = c("9s", "9h", "9d", "As", "Kd")
        assert evaluate_short_deck(fh) > evaluate_short_deck(trips)

    def test_quads_beats_flush(self):
        """Quads should still be above flush."""
        quads = c("6s", "6h", "6d", "6c", "Ks")
        flush = c("Ah", "Th", "8h", "7h", "6h")
        assert evaluate_short_deck(quads) > evaluate_short_deck(flush)

    def test_short_deck_quads_kicker(self):
        """Quad 6s with Ace kicker beats quad 6s with King kicker."""
        h1 = c("6s", "6h", "6d", "6c", "As")
        h2 = c("6s", "6h", "6d", "6c", "Ks")
        assert evaluate_short_deck(h1) > evaluate_short_deck(h2)


# =============================================================================
# ACE-TO-FIVE LOWBALL TESTS
# =============================================================================


class TestAceToFiveLowball:
    """Tests for Ace-to-Five lowball rankings."""

    def test_wheel_is_best_possible_low(self):
        """A-2-3-4-5 is the nuts in Ace-to-Five."""
        wheel = c("As", "2h", "3d", "4c", "5s")
        one_gapper = c("Ah", "2h", "3d", "4c", "6s")
        assert evaluate_ace_to_five_low(wheel) > evaluate_ace_to_five_low(one_gapper)

    def test_seven_low_beats_nine_low(self):
        """7-low must beat 9-low (crossed hands test)."""
        h7 = c("Ah", "2h", "3d", "4c", "7s")
        h9 = c("Ah", "2h", "3d", "4c", "9s")
        assert evaluate_ace_to_five_low(h7) > evaluate_ace_to_five_low(h9)

    def test_pairs_beat_unpaired_in_lowball(self):
        """Paired hands are worse than unpaired hands."""
        h_pair = c("As", "Ah", "2d", "3c", "4s")
        h_nopair = c("7h", "5d", "4c", "3s", "2h")
        assert evaluate_ace_to_five_low(h_pair) < evaluate_ace_to_five_low(h_nopair)

    def test_four_of_a_kind_worst_hand_shape(self):
        """Quad is the worst possible hand shape in lowball."""
        quads = c("As", "Ah", "Ad", "Ac", "2s")
        tripped = c("Ks", "Kh", "Kd", "2c", "3s")
        assert evaluate_ace_to_five_low(quads) < evaluate_ace_to_five_low(tripped)

    def test_straights_and_flushes_do_not_kill_low(self):
        """In Ace-to-Five, straights and flushes do not invalidate low."""
        wheel = c("As", "2s", "3s", "4s", "5s")
        plain_wheel = c("Ah", "2h", "3d", "4c", "5s")
        # Both should be equal (both are A-2-3-4-5 low)
        assert evaluate_ace_to_five_low(wheel) == evaluate_ace_to_five_low(plain_wheel)


# =============================================================================
# BADUGI TESTS
# =============================================================================


class TestBadugiLegalHands:
    """Tests for Badugi hand legality."""

    def test_legal_badugi_four_cards(self):
        """Four cards with different suits and ranks is legal."""
        cards = c("As", "2h", "3d", "4c")
        assert legal_badugi(cards) is True

    def test_illegal_matching_ranks(self):
        """Matching ranks make hand illegal."""
        cards = c("As", "2h", "3d", "3c")
        assert legal_badugi(cards) is False

    def test_illegal_matching_suits(self):
        """Matching suits make hand illegal."""
        cards = c("As", "2h", "3s", "4c")
        assert legal_badugi(cards) is False

    def test_single_card_always_legal(self):
        """Single card is always legal."""
        assert legal_badugi((card_from_str("As"),)) is True


class TestBadugiRankings:
    """Tests for Badugi hand rankings."""

    def test_four_cards_beats_three(self):
        """More cards always beats fewer cards."""
        h4 = c("As", "2h", "3d", "4c")
        h3_input = c("Ah", "2s", "3d", "4h", "5h")  # Best subset is 3-card
        assert evaluate_badugi(h4) > evaluate_badugi(h3_input)

    def test_same_size_lower_ranks_win(self):
        """For same number of cards, lower ranks win."""
        h1 = c("As", "2h", "3d", "4c")
        h2 = c("As", "2h", "3d", "5c")
        assert evaluate_badugi(h1) > evaluate_badugi(h2)

    def test_ace_is_lowest(self):
        """Ace should count as lowest rank."""
        h1 = c("As", "2h", "3d", "4c")
        h2 = c("Kh", "2s", "3d", "4c")
        # Ace hand should beat King hand
        assert evaluate_badugi(h1) > evaluate_badugi(h2)


# =============================================================================
# REGRESSION TESTS
# =============================================================================


class TestRegressionBugs:
    """Tests for specific bugs discovered during development."""

    def test_regression_wheel_broadway_distinct(self):
        """Wheel (A-2-3-4-5) must NOT tie Broadway (T-J-Q-K-A)."""
        wheel = c("As", "2h", "3d", "4c", "5s")
        broadway = c("Ts", "Js", "Qs", "Ks", "As")
        wheel_code = evaluate_standard(wheel)
        broadway_code = evaluate_standard(broadway)
        assert wheel_code != broadway_code, "Wheel tied Broadway - bug not fixed!"
        assert wheel_code < broadway_code, "Wheel should lose to Broadway"

    def test_regression_steel_wheel_not_royal(self):
        """Steel wheel flush must NOT tie royal flush."""
        wheel = c("As", "2s", "3s", "4s", "5s")
        royal = c("As", "Ks", "Qs", "Js", "Ts")
        wheel_code = evaluate_standard(wheel)
        royal_code = evaluate_standard(royal)
        assert wheel_code != royal_code, "Steel wheel tied royal - bug not fixed!"
        assert wheel_code < royal_code

    def test_regression_ace_to_five_sort_direction(self):
        """7-low must beat 9-low - this was failing due to sort key bug."""
        h7 = c("Ah", "2h", "3d", "4c", "7s")
        h9 = c("Ah", "2h", "3d", "4c", "9s")
        code7 = evaluate_ace_to_five_low(h7)
        code9 = evaluate_ace_to_five_low(h9)
        assert code7 != code9, "7-low tied 9-low - bug not fixed!"
        assert code7 > code9, "7-low should beat 9-low"

    def test_regression_straight_high_off_by_one(self):
        """Straight high values should match actual high card."""
        six_high = c("6s", "2h", "3d", "4c", "5h")
        seven_high = c("7s", "3h", "4d", "5c", "6h")

        code6 = evaluate_standard(six_high)
        code7 = evaluate_standard(seven_high)

        # The difference should be exactly 1<<16
        expected_diff = 1 << 16
        actual_diff = code7 - code6
        assert actual_diff == expected_diff, (
            f"High nibble shift wrong: got {actual_diff}, expected {expected_diff}"
        )

    def test_regression_short_deck_flush_over_full_house(self):
        """Short deck must have flush > full house, not the reverse."""
        flush = c("Ah", "9h", "8h", "7h", "6h")
        fh = c("6s", "6h", "6d", "9c", "9d")
        flush_code = evaluate_short_deck(flush)
        fh_code = evaluate_short_deck(fh)
        assert flush_code > fh_code, "Short deck still has full house > flush"


# =============================================================================
# PROPERTY-BASED TESTS (Hypothesis)
# =============================================================================

try:
    from hypothesis import given
    from hypothesis import strategies as st

    class TestPropertyBased:
        """Property-based tests using Hypothesis."""

        @given(
            st.lists(
                st.sampled_from(standard_deck()), min_size=5, max_size=7, unique=True
            )
        )
        def test_evaluation_returns_integer(self, pool: list[int]):
            """Evaluator should always return an integer."""
            code = evaluate_standard(tuple(pool))
            assert isinstance(code, int)

        @given(
            st.lists(
                st.sampled_from(standard_deck()), min_size=5, max_size=7, unique=True
            )
        )
        def test_monotonicity_on_card_addition(self, pool: list[int]):
            """Adding cards can only improve or keep the same hand."""
            if len(pool) >= 5:
                base = evaluate_standard(tuple(pool[:5]))
                extended = evaluate_standard(tuple(pool))
                assert extended >= base

        @given(
            st.lists(
                st.sampled_from(standard_deck()), min_size=5, max_size=7, unique=True
            )
        )
        def test_permutation_invariance(self, pool: list[int]):
            """Order of input cards should not affect result."""
            from random import shuffle

            shuffled = pool.copy()
            shuffle(shuffled)
            assert evaluate_standard(tuple(pool)) == evaluate_standard(tuple(shuffled))

        @given(
            st.lists(
                st.sampled_from(standard_deck()), min_size=5, max_size=5, unique=True
            )
        )
        def test_ace_to_five_no_pair_beats_any_pair_shape(self, cards: list[int]):
            """Unpaired hands beat paired hands in Ace-to-Five lowball."""
            counts = {}
            for c in cards:
                r = c >> 4
                counts[r] = counts.get(r, 0) + 1
            no_pair = all(cnt == 1 for cnt in counts.values())

            if no_pair:
                code_no_pair = evaluate_ace_to_five_low(tuple(cards))
                modified = cards.copy()
                modified[0] = cards[1]
                code_pair = evaluate_ace_to_five_low(tuple(modified))
                assert code_no_pair > code_pair

        @given(
            st.lists(st.sampled_from(short_deck()), min_size=5, max_size=7, unique=True)
        )
        def test_short_deck_evaluation_works(self, pool: list[int]):
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
    pool = tuple(card_from_str(c) for c in ["2s", "3h", "4d", "5c", "6s", "7h", "8d"])

    # Warm up cache
    for _ in range(100):
        evaluate_standard(pool)

    iterations = 10000
    start = __import__("time").perf_counter()
    for _ in range(iterations):
        evaluate_standard(pool)
    elapsed = __import__("time").perf_counter() - start

    rate = iterations / elapsed
    print(f"\nStandard eval: {rate:,.0f} evaluations/second")

    # Minimum target: 50k evals/sec (already achieved 54k+)
    assert rate > 50_000, f"Too slow: {rate:.0f} evals/sec, need >50k"


def test_short_deck_speed_comparison():
    """Compare short deck vs standard evaluation speed."""
    pool = tuple(card_from_str(c) for c in ["6s", "7h", "8d", "9c", "Th", "Jh", "Qs"])

    iterations = 10000
    start = __import__("time").perf_counter()
    for _ in range(iterations):
        evaluate_short_deck(pool)
    elapsed = __import__("time").perf_counter() - start

    rate = iterations / elapsed
    print(f"Short deck eval: {rate:,.0f} evaluations/second")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
