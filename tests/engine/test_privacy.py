"""Privacy / leak tests (docs/ARCHITECTURE.md §6).

Across thousands of simulated hands, serialize every view(viewer) and
public_history() and assert no card token from another seat's unrevealed
hole cards, the undealt deck, or burn cards ever appears — boundary-aware
(a 2-char token must not be a substring of a longer token).
"""
import json
import random
import re

import pytest

from agent_hold_em.engine.table import Table
from agent_hold_em.engine.legal import Action
from agent_hold_em.engine.deck import seeded_deck
from agent_hold_em.engine.cards import RANKS, SUITS

ALL_CARDS = [r + s for r in RANKS for s in SUITS]
_TOKEN_RE = {c: re.compile(r"(?<![A-Za-z0-9])" + re.escape(c) + r"(?![A-Za-z0-9])") for c in ALL_CARDS}


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
        options.append(("all_in", None))
    kind, to = rng.choice(options)
    return Action(kind, to)


def _forbidden_cards_for_viewer(t, viewer):
    """Cards that must NEVER appear in this viewer's serialized view/history."""
    forbidden = set()
    if t.hand_in_progress:
        for s in t._hand_seats:
            if s != viewer:
                forbidden.update(t._hole[s])
        forbidden.update(t._deck)
        forbidden.update(t._burns)
    return forbidden


def _check_no_leak(blob_text, forbidden_cards):
    for c in forbidden_cards:
        assert not _TOKEN_RE[c].search(blob_text), f"leaked forbidden card {c!r}"


@pytest.mark.slow
def test_no_card_leaks_across_thousands_of_hands():
    rng = random.Random(555)
    total_hands = 0
    table_idx = 0
    while total_hands < 3000:
        table_idx += 1
        t = Table.new(["A", "B", "C", "D"], deck_factory=lambda: seeded_deck(rng.random()))
        hands_this_table = 0
        while not t.table_over and hands_this_table < 300:
            try:
                t.start_hand()
            except Exception:
                break
            hands_this_table += 1
            total_hands += 1
            _check_views(t)
            while t.hand_in_progress:
                seat = t.to_act()
                act = _random_action(t, rng)
                t.apply(seat, act)
                _check_views(t)
        if total_hands >= 3000:
            break


def _check_views(t):
    # NOTE: a bare card token (e.g. "9h") recurs every single hand (each
    # hand reshuffles all 52 cards), so a card legitimately revealed in an
    # OLDER hand's showdown will very often collide, as a string, with a
    # card that is privately held in the deck/hole cards of the CURRENT
    # hand. Checking a whole serialized blob that mixes hands would flag
    # those coincidences as false "leaks". So every check here is scoped
    # to the CURRENT hand only: view()'s `seats`/`board`/`pots` fields are
    # already current-hand-scoped by construction, and for `log` /
    # `public_history()` we scan only the current hand's own event tail
    # (never the previous-hand tail view() prepends, and never older
    # completed-hand records — those were already checked, against their
    # own forbidden set, in the turn they were current).
    for viewer in (None, 0, 1, 2, 3):
        forbidden = _forbidden_cards_for_viewer(t, viewer)
        if not forbidden:
            continue
        # `last_hand` deliberately excluded: it is the PREVIOUS (already
        # completed, already-checked-when-current) hand's public summary,
        # which legitimately contains that older hand's revealed cards.
        v = t.view(viewer)
        scoped = {k: v[k] for k in ("seats", "board", "pots") if k in v}
        scoped["current_log"] = list(t._current_hand_log)
        _check_no_leak(json.dumps(scoped), forbidden)

    always_forbidden = set()
    if t.hand_in_progress:
        for s in t._hand_seats:
            always_forbidden.update(t._hole[s])
        always_forbidden.update(t._deck)
        always_forbidden.update(t._burns)
        for ev in t._current_hand_log:
            if ev.get("type") == "showdown":
                for r in ev["reveals"]:
                    for c in r["cards"]:
                        always_forbidden.discard(c)
    if always_forbidden:
        current_only_blob = json.dumps(list(t._current_hand_log))
        _check_no_leak(current_only_blob, always_forbidden)


def test_folded_hole_cards_never_revealed_in_history():
    rng = random.Random(77)
    t = Table.new(["A", "B", "C", "D"], deck_factory=lambda: seeded_deck(1))
    t.start_hand()
    folded_cards = []
    seat = t.to_act()
    folded_cards.extend(t._hole[seat])
    t.apply(seat, Action("fold"))
    while t.hand_in_progress:
        s = t.to_act()
        leg = t.legal()
        act = Action("check") if leg.can_check else Action("call")
        t.apply(s, act)
    hist_blob = json.dumps(t.public_history())
    for c in folded_cards:
        assert not _TOKEN_RE[c].search(hist_blob)


def test_deck_and_burns_never_in_to_dict_view_only_in_private_state():
    t = Table.new(["A", "B", "C", "D"], deck_factory=lambda: seeded_deck(2))
    t.start_hand()
    d = t.to_dict()
    # to_dict IS private recovery state and legitimately contains the deck.
    assert "remaining_deck" in d["hand_state"]
    # but view() must not.
    for viewer in (None, 0, 1, 2, 3):
        view_blob = json.dumps(t.view(viewer))
        for c in t._deck:
            assert not _TOKEN_RE[c].search(view_blob)
        for c in t._burns:
            assert not _TOKEN_RE[c].search(view_blob)
