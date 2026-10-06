"""Hand evaluator: best-5-of-N poker hand ranking with human-readable labels.

Strength keys are tuples `(category, tiebreak...)` where a LARGER tuple
(standard Python tuple comparison) is a STRICTLY better hand — categories
already sort correctly against each other because the first tiebreak of a
lower category never reaches the numeric range that would let it out-rank
the category slot of a higher one (category is always compared first).

Categories (higher = better):
    8 straight flush (royal is just ace-high straight flush)
    7 four of a kind
    6 full house
    5 flush
    4 straight
    3 three of a kind
    2 two pair
    1 pair
    0 high card

Wheel (A-2-3-4-5) is handled as a straight with high card = 5 (both plain
and straight-flush forms, i.e. "steel wheel").
"""
import itertools

from .cards import card_rank, card_suit, RANK_NAMES, RANK_NAMES_PLURAL


def evaluate_best5(cards):
    """Return the strength key tuple for EXACTLY 5 cards (2-char strings)."""
    if len(cards) != 5:
        raise ValueError("evaluate_best5 requires exactly 5 cards")
    ranks = [card_rank(c) for c in cards]
    suits = [card_suit(c) for c in cards]
    is_flush = suits[0] == suits[1] == suits[2] == suits[3] == suits[4]

    counts = [0] * 15
    for r in ranks:
        counts[r] += 1

    distinct = sorted((r for r in range(2, 15) if counts[r]), reverse=True)
    straight_high = None
    if len(distinct) == 5:
        if distinct[0] - distinct[4] == 4:
            straight_high = distinct[0]
        elif distinct == [14, 5, 4, 3, 2]:
            straight_high = 5  # wheel

    if straight_high and is_flush:
        return (8, straight_high)

    groups = sorted(
        ((r, counts[r]) for r in range(2, 15) if counts[r]),
        key=lambda rc: (-rc[1], -rc[0]),
    )
    pattern = tuple(c for _, c in groups)
    ranks_desc = sorted(ranks, reverse=True)

    if pattern == (4, 1):
        return (7, groups[0][0], groups[1][0])
    if pattern == (3, 2):
        return (6, groups[0][0], groups[1][0])
    if is_flush:
        return (5,) + tuple(ranks_desc)
    if straight_high:
        return (4, straight_high)
    if pattern == (3, 1, 1):
        return (3, groups[0][0], groups[1][0], groups[2][0])
    if pattern == (2, 2, 1):
        return (2, groups[0][0], groups[1][0], groups[2][0])
    if pattern == (2, 1, 1, 1):
        return (1, groups[0][0], groups[1][0], groups[2][0], groups[3][0])
    return (0,) + tuple(ranks_desc)


def evaluate_seven(cards):
    """Best 5-of-N (N>=5, typically 7) evaluation.

    Returns (key, best5_cards) — key is the strength tuple from
    evaluate_best5 for the winning subset, best5_cards is that subset
    (list of 2-char card strings) in the order they appeared in `cards`.
    """
    if len(cards) < 5:
        raise ValueError("evaluate_seven requires at least 5 cards")
    if len(cards) == 5:
        return evaluate_best5(cards), list(cards)
    best_key = None
    best_combo = None
    for combo in itertools.combinations(cards, 5):
        key = evaluate_best5(combo)
        if best_key is None or key > best_key:
            best_key = key
            best_combo = combo
    return best_key, list(best_combo)


def hand_label(key):
    """Human-readable label for a strength key tuple."""
    cat = key[0]
    if cat == 8:
        high = key[1]
        if high == 14:
            return "Royal Flush"
        return f"Straight Flush, {RANK_NAMES[high]}-high"
    if cat == 7:
        quad, kicker = key[1], key[2]
        return f"Four of a Kind, {RANK_NAMES_PLURAL[quad]}"
    if cat == 6:
        trip, pair = key[1], key[2]
        return f"Full House, {RANK_NAMES_PLURAL[trip]} over {RANK_NAMES_PLURAL[pair]}"
    if cat == 5:
        high = key[1]
        return f"Flush, {RANK_NAMES[high]}-high"
    if cat == 4:
        high = key[1]
        return f"Straight, {RANK_NAMES[high]}-high"
    if cat == 3:
        trip = key[1]
        return f"Three of a Kind, {RANK_NAMES_PLURAL[trip]}"
    if cat == 2:
        p1, p2 = key[1], key[2]
        return f"Two Pair, {RANK_NAMES_PLURAL[p1]} and {RANK_NAMES_PLURAL[p2]}"
    if cat == 1:
        pair = key[1]
        return f"Pair of {RANK_NAMES_PLURAL[pair]}"
    high = key[1]
    return f"High Card, {RANK_NAMES[high]}"
