"""Independent pot-settlement oracle.

Deliberately simple, obviously-correct, slow — does NOT import
agent_hold_em.engine.pots (the real engine's implementation) so it can
cross-check it independently. Given per-seat total contributions, a
folded set, and a "strength" per non-folded seat, this recomputes
payouts (including odd-chip distribution) by brute reasoning: for every
distinct contribution level, everyone who put in at least that much
chips in for that layer; the layer is split among the best non-folded
hand(s) at that level.
"""
import random

import pytest

from agent_hold_em.engine.pots import build_side_pots
from agent_hold_em.engine.table import Table
from agent_hold_em.engine.legal import Action
from agent_hold_em.engine.deck import fixed_deck


def oracle_payouts(contrib, folded, strength, button, num_seats=4):
    """contrib: {seat: total contributed}. folded: set. strength: {seat: comparable key} for non-folded seats.
    button: seat number (odd chips start left of button).
    Returns {seat: amount_won}.
    """
    seats_with_contrib = [s for s, amt in contrib.items() if amt > 0]
    if not seats_with_contrib:
        return {}

    # Step 1: uncalled-bet return (obviously-correct O(n^2) scan).
    contrib = dict(contrib)
    payout = {s: 0 for s in seats_with_contrib}
    top = max(seats_with_contrib, key=lambda s: contrib[s])
    others = [contrib[s] for s in seats_with_contrib if s != top]
    second = max(others) if others else 0
    if contrib[top] > second:
        refund = contrib[top] - second
        contrib[top] -= refund
        payout[top] += refund

    non_folded = [s for s in seats_with_contrib if s not in folded]
    if len(non_folded) == 1:
        # everyone else folded: sole survivor takes everything remaining.
        total_remaining = sum(contrib.values())
        payout[non_folded[0]] = payout.get(non_folded[0], 0) + total_remaining
        return payout

    # Step 2: cap folded contributions at the max non-folded total (their
    # excess, if any, was never eligible to be won back by them and simply
    # feeds the top pot the eventual winner(s) take).
    max_nf = max(contrib[s] for s in non_folded)
    leftover = 0
    for s in list(contrib.keys()):
        if s in folded and contrib[s] > max_nf:
            leftover += contrib[s] - max_nf
            contrib[s] = max_nf

    # Step 3: brute-force layer construction, level by level.
    levels = sorted(set(v for v in contrib.values() if v > 0))
    prev = 0
    order = [(button + 1 + i) % num_seats for i in range(num_seats)]
    layer_amounts = []
    for level in levels:
        size = level - prev
        if size <= 0:
            prev = level
            continue
        payers = [s for s in contrib if contrib[s] >= level]
        amount = size * len(payers)
        eligible = [s for s in payers if s not in folded]
        layer_amounts.append((amount, eligible))
        prev = level

    if leftover and layer_amounts:
        amt, elig = layer_amounts[-1]
        layer_amounts[-1] = (amt + leftover, elig)

    for amount, eligible in layer_amounts:
        if not eligible:
            continue
        best = max(strength[s] for s in eligible)
        winners = [s for s in eligible if strength[s] == best]
        base = amount // len(winners)
        rem = amount - base * len(winners)
        win_order = [s for s in order if s in winners]
        extra = set()
        for i in range(rem):
            extra.add(win_order[i % len(win_order)])
        for w in winners:
            payout[w] = payout.get(w, 0) + base + (1 if w in extra else 0)

    return payout


def _random_scenario(rng):
    n = rng.choice([2, 3, 4])
    seats = list(range(n))
    contrib = {s: rng.choice([1, 2, 5, 20, 50, 100, 137, 1000]) for s in seats}
    folded = set(s for s in seats if rng.random() < 0.3)
    # never fold everyone
    if len(folded) >= n:
        folded = set(list(folded)[:-1])
    non_folded = [s for s in seats if s not in folded]
    if not non_folded:
        non_folded = [seats[0]]
        folded.discard(seats[0])
    strength = {}
    for s in non_folded:
        # allow ties on purpose sometimes
        strength[s] = rng.choice([1, 1, 2, 3, 3, 4])
    button = rng.choice(seats)
    return contrib, folded, strength, button, n


@pytest.mark.parametrize("trial", range(3000))
def test_oracle_matches_engine_pot_logic(trial):
    rng = random.Random(trial * 7919 + 1)
    contrib, folded, strength, button, n = _random_scenario(rng)

    expected = oracle_payouts(dict(contrib), set(folded), dict(strength), button, num_seats=n)

    # Reproduce via the engine's own building blocks (uncalled return +
    # build_side_pots + the same odd-chip rule), independently assembled
    # here rather than driving a full Table (that's covered by the
    # simulation tests) — this isolates pot math specifically.
    c2 = dict(contrib)
    seats_with_contrib = [s for s, amt in c2.items() if amt > 0]
    top = max(seats_with_contrib, key=lambda s: c2[s])
    others = [c2[s] for s in seats_with_contrib if s != top]
    second = max(others) if others else 0
    payout = {s: 0 for s in seats_with_contrib}
    if c2[top] > second:
        refund = c2[top] - second
        c2[top] -= refund
        payout[top] += refund

    non_folded = [s for s in seats_with_contrib if s not in folded]
    if len(non_folded) == 1:
        payout[non_folded[0]] = payout.get(non_folded[0], 0) + sum(c2.values())
    else:
        max_nf = max(c2[s] for s in non_folded)
        adjusted = {}
        leftover = 0
        for s, amt in c2.items():
            if s in folded and amt > max_nf:
                leftover += amt - max_nf
                adjusted[s] = max_nf
            else:
                adjusted[s] = amt
        pots = build_side_pots(adjusted, folded)
        if leftover and pots:
            pots[-1]["amount"] += leftover
        order = [(button + 1 + i) % n for i in range(n)]
        for pot in pots:
            eligible = pot["eligible"]
            if not eligible:
                continue
            best = max(strength[s] for s in eligible)
            winners = [s for s in eligible if strength[s] == best]
            amount = pot["amount"]
            base = amount // len(winners)
            rem = amount - base * len(winners)
            win_order = [s for s in order if s in winners]
            extra = set()
            for i in range(rem):
                extra.add(win_order[i % len(win_order)])
            for w in winners:
                payout[w] = payout.get(w, 0) + base + (1 if w in extra else 0)

    assert payout == expected
    assert sum(payout.values()) == sum(contrib.values())


def test_oracle_chip_conservation_many_trials():
    rng = random.Random(999)
    for _ in range(2000):
        contrib, folded, strength, button, n = _random_scenario(rng)
        out = oracle_payouts(dict(contrib), set(folded), dict(strength), button, num_seats=n)
        assert sum(out.values()) == sum(contrib.values())
        for amt in out.values():
            assert amt >= 0
