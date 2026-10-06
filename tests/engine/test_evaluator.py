import itertools
import random

import pytest

from agent_hold_em.engine.cards import full_deck
from agent_hold_em.engine.evaluator import evaluate_best5, evaluate_seven, hand_label

# Known category counts over all C(52,5) = 2,598,960 five-card hands.
EXPECTED_COUNTS = {
    8: 40,        # straight flush (royal included)
    7: 624,       # four of a kind
    6: 3744,      # full house
    5: 5108,      # flush (incl. straight flushes excluded since counted separately below)
    4: 10200,     # straight (incl. straight flushes excluded)
    3: 54912,     # three of a kind
    2: 123552,    # two pair
    1: 1098240,   # pair
    0: 1302540,   # high card
}
TOTAL_HANDS = 2_598_960


@pytest.mark.slow
def test_exhaustive_five_card_category_counts():
    deck = full_deck()
    counts = {k: 0 for k in EXPECTED_COUNTS}
    total = 0
    for combo in itertools.combinations(deck, 5):
        key = evaluate_best5(combo)
        counts[key[0]] += 1
        total += 1
    assert total == TOTAL_HANDS
    assert counts == EXPECTED_COUNTS


def test_seven_card_equals_max_of_21_subsets_random():
    deck = full_deck()
    rng = random.Random(12345)
    for _ in range(20000):
        hand = rng.sample(deck, 7)
        key, best5 = evaluate_seven(hand)
        best_manual = max(evaluate_best5(c) for c in itertools.combinations(hand, 5))
        assert key == best_manual
        assert len(best5) == 5
        assert set(best5).issubset(set(hand))


def test_wheel_is_five_high_straight():
    wheel = ["Ah", "2d", "3c", "4s", "5h"]
    key = evaluate_best5(wheel)
    assert key[0] == 4
    assert key[1] == 5
    assert hand_label(key) == "Straight, Five-high"


def test_steel_wheel_is_straight_flush_five_high():
    wheel_sf = ["Ah", "2h", "3h", "4h", "5h"]
    key = evaluate_best5(wheel_sf)
    assert key[0] == 8
    assert key[1] == 5


def test_broadway_straight_beats_wheel():
    broadway = evaluate_best5(["Th", "Jd", "Qc", "Ks", "Ah"])
    wheel = evaluate_best5(["Ah", "2d", "3c", "4s", "5h"])
    assert broadway > wheel
    assert broadway[1] == 14


def test_flush_beats_straight():
    flush = evaluate_best5(["2h", "5h", "9h", "Jh", "Kh"])
    straight = evaluate_best5(["6c", "7d", "8h", "9s", "Th"])
    assert flush > straight
    assert flush[0] == 5 and straight[0] == 4


def test_full_house_from_two_trips_uses_best_trip_as_trip():
    # 7-card board makes trips of both 9s and 6s available; best full house
    # must use the higher trip as the triple and the other as the pair.
    hole = ["9h", "9d"]
    board = ["9c", "6h", "6d", "6s", "2c"]
    key, best5 = evaluate_seven(hole + board)
    assert key[0] == 6
    assert key[1] == 9  # trip rank
    assert key[2] == 6  # pair rank
    assert hand_label(key) == "Full House, Nines over Sixes"


def test_two_pair_counterfeited_by_board():
    # Player holds a pocket pair that gets counterfeited: board pairs higher.
    hole = ["3h", "3d"]
    board = ["Ah", "Ad", "Kc", "Kh", "2s"]
    key, best5 = evaluate_seven(hole + board)
    # best available: two pair Aces and Kings (board), 3s are the worst pair
    assert key[0] == 2
    assert key[1] == 14 and key[2] == 13


def test_board_plays_ties_two_players():
    board = ["Th", "Jh", "Qh", "Kh", "Ah"]  # royal flush on board
    h1 = evaluate_best5(board)
    key1, _ = evaluate_seven(["2c", "3d"] + board)
    key2, _ = evaluate_seven(["7c", "8d"] + board)
    assert key1 == key2 == h1


def test_kicker_ordering():
    a = evaluate_best5(["Ah", "Ad", "Kc", "Qd", "2s"])
    b = evaluate_best5(["Ac", "As", "Kh", "Jd", "2c"])
    assert a > b  # pair of aces, K kicker beats pair of aces, J kicker


def test_labels():
    assert hand_label(evaluate_best5(["Th", "Jh", "Qh", "Kh", "Ah"])) == "Royal Flush"
    assert hand_label(evaluate_best5(["9h", "9d", "9c", "9s", "2h"])) == "Four of a Kind, Nines"
    assert hand_label(evaluate_best5(["9h", "9d", "9c", "4s", "4h"])) == "Full House, Nines over Fours"
    assert hand_label(evaluate_best5(["2h", "5h", "9h", "Jh", "Kh"])) == "Flush, King-high"
    assert hand_label(evaluate_best5(["Ah", "2d", "3c", "4s", "5h"])) == "Straight, Five-high"
    assert hand_label(evaluate_best5(["9h", "9d", "9c", "4s", "2h"])) == "Three of a Kind, Nines"
    assert hand_label(evaluate_best5(["Kh", "Kd", "7c", "7s", "2h"])) == "Two Pair, Kings and Sevens"
    assert hand_label(evaluate_best5(["Kh", "Kd", "7c", "9s", "2h"])) == "Pair of Kings"
    assert hand_label(evaluate_best5(["Kh", "9d", "7c", "4s", "2h"])) == "High Card, King"
