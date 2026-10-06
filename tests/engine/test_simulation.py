"""Property / simulation tests: thousands of randomized full hands.

After EVERY action we assert: chip conservation, no negative stacks,
52 unique cards dealt with no duplicates, correct board sizes per street,
to_act always a live non-all-in seat, legal() bounds self-consistent,
version strictly increasing, and a to_dict()/from_dict() round trip at a
random point yields an identical view() for every viewer and identical
subsequent evolution.
"""
import random
import time

import pytest

from agent_hold_em.engine.table import Table
from agent_hold_em.engine.legal import Action
from agent_hold_em.engine.deck import seeded_deck

TOTAL_CHIPS = 4000
MIN_HANDS_TARGET = 5000


def _random_action(t, rng):
    leg = t.legal()
    options = []
    if leg.can_fold:
        options.append(("fold", None))
    if leg.can_check:
        options.append(("check", None))
    if leg.can_call:
        options.append(("call", None))
    if leg.raise_kind:
        options.append((leg.raise_kind, leg.min_to))
        if leg.max_to > leg.min_to:
            mid = (leg.min_to + leg.max_to) // 2
            if mid > leg.min_to:
                options.append((leg.raise_kind, mid))
        options.append(("all_in", None))
    kind, to = rng.choice(options)
    return Action(kind, to)


def _assert_invariants(t, seen_cards_by_hand):
    total = sum(s["stack"] for s in t.seats)
    if t.hand_in_progress:
        total += sum(t._committed.values()) + sum(t._total_in_pot.values())
    assert total == TOTAL_CHIPS, f"chip conservation violated: {total}"
    for s in t.seats:
        assert s["stack"] >= 0

    if t.hand_in_progress:
        expected_board = {"preflop": 0, "flop": 3, "turn": 4, "river": 5}[t._street]
        assert len(t._board) == expected_board
        to_act = t.to_act()
        if to_act is not None:
            assert t._pstate[to_act] == "active"
        # 52 unique cards: hole + board + burns + remaining deck
        all_cards = []
        for s in t._hand_seats:
            all_cards.extend(t._hole[s])
        all_cards.extend(t._board)
        all_cards.extend(t._burns)
        all_cards.extend(t._deck)
        assert len(all_cards) == 52
        assert len(set(all_cards)) == 52

        leg = t.legal()
        if leg is not None:
            if leg.min_to is not None:
                assert leg.min_to <= leg.max_to
            assert leg.all_in_to == leg.committed + leg.stack


def _play_one_table(seed, rng, do_roundtrip):
    t = Table.new(["A", "B", "C", "D"], deck_factory=lambda: seeded_deck(rng.random()))
    hands_played = 0
    last_version = t.version
    roundtrip_done = not do_roundtrip
    while not t.table_over:
        try:
            t.start_hand()
        except Exception:
            break
        assert t.version > last_version
        last_version = t.version
        hands_played += 1
        _assert_invariants(t, None)
        while t.hand_in_progress:
            act = _random_action(t, rng)
            seat = t.to_act()
            t.apply(seat, act)
            assert t.version > last_version
            last_version = t.version
            _assert_invariants(t, None)

            if not roundtrip_done and rng.random() < 0.02:
                roundtrip_done = True
                views_before = [t.view(v) for v in (None, 0, 1, 2, 3)]
                d = t.to_dict()
                t2 = Table.from_dict(d)
                views_after = [t2.view(v) for v in (None, 0, 1, 2, 3)]
                assert views_before == views_after
                assert t2.version == t.version
                assert t2.to_act() == t.to_act()
                # continue driving BOTH tables identically from here and confirm
                # they stay in lockstep for a few more actions.
                for _ in range(5):
                    if not t.hand_in_progress:
                        break
                    rng_state = rng.getstate()
                    a1 = _random_action(t, rng)
                    rng.setstate(rng_state)
                    a2 = _random_action(t2, rng)
                    s1 = t.to_act()
                    s2 = t2.to_act()
                    assert s1 == s2
                    t.apply(s1, a1)
                    t2.apply(s2, a2)
                    assert t.view(None) == t2.view(None)
                    assert t.to_dict() == t2.to_dict()
        if hands_played > 400:
            break  # safety cap per table
    return hands_played


@pytest.mark.slow
def test_simulation_thousands_of_hands_chip_conservation_and_roundtrip():
    rng = random.Random(20260926)
    total_hands = 0
    start = time.time()
    table_idx = 0
    while total_hands < MIN_HANDS_TARGET:
        table_idx += 1
        do_rt = (table_idx % 5 == 0)
        played = _play_one_table(table_idx, rng, do_rt)
        total_hands += played
        if played == 0:
            # degenerate (e.g. immediate table_over) — avoid infinite loop
            if table_idx > MIN_HANDS_TARGET:
                break
    elapsed = time.time() - start
    print(f"\n[simulation] {total_hands} hands across {table_idx} tables in {elapsed:.2f}s "
          f"({total_hands / elapsed:.1f} hands/s)")
    assert total_hands >= MIN_HANDS_TARGET


def test_simulation_1000_hands_performance_note():
    rng = random.Random(42)
    total_hands = 0
    start = time.time()
    table_idx = 0
    while total_hands < 1000:
        table_idx += 1
        played = _play_one_table(table_idx, rng, False)
        total_hands += played
    elapsed = time.time() - start
    print(f"\n[perf] {total_hands} hands in {elapsed:.3f}s ({total_hands/elapsed:.1f} hands/s)")
    assert total_hands >= 1000
