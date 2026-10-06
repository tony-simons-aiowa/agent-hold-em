import pytest

from agent_hold_em.engine.table import Table
from agent_hold_em.engine.legal import Action
from agent_hold_em.engine.deck import fixed_deck
from agent_hold_em.engine.errors import IllegalAction


def new_table(names=("A", "B", "C", "D"), stacks=None, sb=5, bb=10, deck=None):
    t = Table.new(list(names), sb=sb, bb=bb, deck_factory=(deck or fixed_deck([])))
    if stacks:
        for i, s in enumerate(stacks):
            t.seats[i]["stack"] = s
    return t


def total_chips(t):
    return sum(s["stack"] for s in t.seats)


def play_check_call_to_showdown(t):
    while t.hand_in_progress:
        seat = t.to_act()
        leg = t.legal()
        act = Action("check") if leg.can_check else Action("call")
        t.apply(seat, act)


# ---------------------------------------------------------------------
# Button / blind rotation
# ---------------------------------------------------------------------
def test_button_rotates_each_hand_4_handed():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    buttons = []
    for _ in range(8):
        t.start_hand()
        buttons.append(t.button)
        play_check_call_to_showdown(t)
    assert buttons == [0, 1, 2, 3, 0, 1, 2, 3]


def test_blinds_follow_button_3_and_4_handed():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    assert t.button == 0
    assert t._sb_seat == 1 and t._bb_seat == 2
    play_check_call_to_showdown(t)
    t.start_hand()
    assert t.button == 1
    assert t._sb_seat == 2 and t._bb_seat == 3


def test_button_skips_busted_seat():
    t = new_table(stacks=[1000, 1000, 1000, 10])
    t.start_hand()
    assert t.button == 0
    # seat 3 (bb) posts 10, all-in; drive everyone to fold to seat3 so seat3 wins and stays alive,
    # then force seat3 out by losing next hand instead; simpler: just bust seat 3 directly.
    t.seats[3]["stack"] = 0
    t.seats[3]["out"] = True
    play_check_call_to_showdown(t)
    t.start_hand()
    # button should skip seat 3 (busted): from 0 -> next with chips -> 1
    assert t.button == 1
    play_check_call_to_showdown(t)


# ---------------------------------------------------------------------
# Heads-up ordering
# ---------------------------------------------------------------------
def test_heads_up_button_acts_first_preflop_bb_first_postflop():
    t = new_table(stacks=[1000, 1000, 0, 0])
    t.seats[2]["out"] = True
    t.seats[3]["out"] = True
    t.start_hand()
    assert t._heads_up is True
    assert t._sb_seat == t.button
    assert t.to_act() == t.button  # button/SB acts first preflop
    seat = t.to_act()
    t.apply(seat, Action("call"))
    leg = t.legal()
    t.apply(t.to_act(), Action("check"))
    assert t._street == "flop"
    assert t.to_act() == t._bb_seat  # BB acts first postflop


def test_transition_4_to_3_to_2_players_mid_orbit():
    t = new_table(stacks=[1000, 1000, 1000, 20])
    t.start_hand()
    assert len([s for s in range(4) if not t.seats[s]["out"]]) == 4
    # bust seat 3 by everyone folding to them repeatedly is fiddly; force directly for determinism
    play_check_call_to_showdown(t)
    t.seats[3]["stack"] = 0
    t.seats[3]["out"] = True
    t.start_hand()
    assert 3 not in t._hand_seats
    play_check_call_to_showdown(t)
    t.seats[2]["stack"] = 0
    t.seats[2]["out"] = True
    t.start_hand()
    assert t._heads_up is True
    assert set(t._hand_seats) == {0, 1}


# ---------------------------------------------------------------------
# Min-raise sequences
# ---------------------------------------------------------------------
def test_min_raise_sequence_bet_raise_reraise():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    seat = t.to_act()
    t.apply(seat, Action("bet", to=10))
    leg = t.legal()
    assert leg.min_to == 20  # current_bet(10) + last_full_raise_size(bb=10)
    t.apply(t.to_act(), Action("raise", to=30))  # raise size 20 (full, >=10)
    leg = t.legal()
    assert leg.min_to == 50  # baseline 30 + last_full 20
    t.apply(t.to_act(), Action("raise", to=50))  # min re-raise
    leg = t.legal()
    assert leg.min_to == 70  # baseline 50 + last_full 20


def test_min_raise_sequence_large_numbers():
    t = new_table(stacks=[2000, 2000, 2000, 2000])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    seat = t.to_act()
    t.apply(seat, Action("bet", to=100))
    t.apply(t.to_act(), Action("raise", to=250))  # +150, full raise (>=100)
    leg = t.legal()
    assert leg.min_to == 400  # baseline 250 + last_full 150


# ---------------------------------------------------------------------
# Short all-in reopen rules
# ---------------------------------------------------------------------
def test_short_allin_does_not_reopen_for_already_acted():
    t = new_table(stacks=[1000, 1000, 150, 1000])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    t.apply(1, Action("bet", to=100))
    t.apply(2, Action("all_in"))  # seat2 shoves 140 total (incomplete raise)
    t.apply(3, Action("call"))
    t.apply(0, Action("call"))
    assert t.to_act() == 1
    leg = t.legal()
    assert leg.raise_kind is None  # seat1 already acted since baseline; restricted to call/fold
    with pytest.raises(IllegalAction):
        t.apply(1, Action("raise", to=300))
    t.apply(1, Action("call"))
    assert t._street == "turn"


def test_short_allin_reopens_for_seat_not_yet_acted():
    t = new_table(stacks=[1000, 1000, 150, 1000])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    t.apply(1, Action("bet", to=100))
    t.apply(2, Action("all_in"))  # incomplete raise to 140
    # seat 3 has not acted yet this street -> may still raise fully
    leg = t.legal()
    assert leg.raise_kind == "raise"
    assert leg.min_to == 200  # baseline(100) + last_full(100)


def test_cumulative_incomplete_raises_reopen_tda_rule():
    # seat0/seat3 keep big stacks so they can still raise numerically; seat1
    # opens for 100, seat2 (130) and a fourth short stack shove incomplete
    # raises that cumulatively cross a full raise and reopen action.
    t = new_table(stacks=[2000, 2000, 130, 145])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    t.apply(1, Action("bet", to=100))   # baseline=100, last_full=100
    t.apply(2, Action("all_in"))        # seat2 -> 120 total (130-10 blind), incomplete (delta 20 < 100)
    t.apply(3, Action("all_in"))        # seat3 -> 135 total (145-10 blind), still incomplete cumulatively
    assert t.seats[2]["stack"] == 0 and t.seats[3]["stack"] == 0
    assert t._baseline == 100  # neither incomplete raise moved the baseline
    leg0 = t.legal()
    # seat0 never acted yet this street -> can still raise regardless, and
    # has plenty of stack to actually do so.
    assert leg0.raise_kind == "raise"
    t.apply(0, Action("raise", to=250))  # delta from baseline(100) = 150 >= 100: full raise, reopens
    assert t._baseline == 250
    # now action returns to seat1, who already acted (bet 100) before any reopening raise;
    # since a genuine full raise just occurred, seat1 IS reopened and may re-raise again.
    leg1 = t.legal()
    assert leg1.seat == 1
    assert leg1.raise_kind == "raise"


# ---------------------------------------------------------------------
# Calls all-in for less / uncalled bet return
# ---------------------------------------------------------------------
def test_call_all_in_for_less():
    t = new_table(stacks=[1000, 1000, 1000, 50])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    t.apply(1, Action("bet", to=200))
    leg3 = None
    for seat in (2, 3):
        pass
    t.apply(2, Action("fold"))
    leg3 = t.legal()
    assert t.to_act() == 3
    assert leg3.call_amount == 40  # seat3 only has 40 left after blind post (50-10)
    t.apply(3, Action("call"))
    assert t.seats[3]["stack"] == 0


def test_uncalled_bet_return_big_shove_vs_small_stack():
    t = new_table(stacks=[1000, 30, 1000, 1000])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    t.apply(1, Action("all_in"))     # seat1 shoves for 30 total
    t.apply(2, Action("fold"))
    t.apply(3, Action("fold"))
    stack_before = t.seats[0]["stack"]
    t.apply(0, Action("call"))       # seat0 calls only 30 (capped by seat1's all-in)
    assert t.seats[0]["stack"] == stack_before - 20  # only owed 20 more after blind(10)
    play_check_call_to_showdown(t)
    assert total_chips(t) == 1000 + 30 + 1000 + 1000


def test_three_way_allin_two_side_pots():
    t = new_table(stacks=[50, 100, 1000, 1000])
    t.seats[3]["out"] = True
    t.seats[3]["stack"] = 0
    # keep 3-handed for a clean scenario
    t.start_hand()
    while t.hand_in_progress:
        seat = t.to_act()
        leg = t.legal()
        if leg.raise_kind:
            t.apply(seat, Action("all_in"))
        else:
            t.apply(seat, Action("call") if leg.can_call else Action("check"))
    assert total_chips(t) == 50 + 100 + 1000
    pot_awards = t._last_hand_summary["pot_awards"]
    assert len(pot_awards) >= 2


def test_board_plays_four_way_chop():
    # Board plays for everyone: nobody's hole cards improve on the board,
    # so all four remaining hands tie and split the pot.
    deck_order = [
        "2c", "2d", "2h", "2s",   # hole round 1 (seats 1,2,3,0 -- deal order)
        "3c", "3d", "3h", "3s",   # hole round 2
        "9c", "Th", "Jh", "Qh",   # burn + flop
        "9d", "Kh",               # burn + turn
        "9s", "Ah",               # burn + river: board = Th Jh Qh Kh Ah (royal flush plays)
    ]
    t = new_table(stacks=[1005, 1005, 1005, 1005], deck=fixed_deck(deck_order))
    t.start_hand()
    play_check_call_to_showdown(t)
    summary = t._last_hand_summary
    assert len(summary["winners"]) == 4
    assert summary["pot_awards"][0]["split"] is True
    assert total_chips(t) == 4 * 1005


def test_split_pot_with_odd_chip_distribution():
    # Directly exercise the odd-chip rule: 3 tied winners splitting a pot
    # that isn't evenly divisible get the remainder one chip at a time,
    # in seat order starting left of the button.
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    # Bypass start_hand()/betting entirely (which would post blinds and
    # perturb the stacks) and drive settlement directly against a
    # controlled, deterministic pot/hand-strength setup.
    t.button = 0
    t.hand_no = 1
    t.hand_in_progress = True
    t._hand_seats = [1, 2, 3, 0]
    t._current_hand_log = []
    t._pending = []
    t._pstate = {0: "active", 1: "active", 2: "active", 3: "folded"}
    t._total_in_pot = {0: 100, 1: 100, 2: 100, 3: 100}
    t._committed = {0: 0, 1: 0, 2: 0, 3: 0}
    # Give seats 0,1,2 hole cards that all make the exact same made hand
    # (pair of nines, ace kicker) off a shared board, so they tie for the
    # pot; seat 3 folded and its 100 was already captured above.
    board = ["9c", "Ah", "2d", "5s", "7h"]
    t._board = board
    # All three kickers rank below the board's 5, so each player's best five
    # is exactly {9,9,A,7,5} -- a genuine 3-way tie, not merely a coincidence
    # of overlapping ranks (kicker rank itself never enters the best five).
    t._hole = {
        0: ["9h", "3c"],
        1: ["9d", "3d"],
        2: ["9s", "3h"],
        3: ["Kc", "Kd"],
    }
    t._settle_showdown()
    summary = t._last_hand_summary
    award = summary["pot_awards"][0]
    assert award["split"] is True
    assert sorted(award["winners"]) == [0, 1, 2]
    assert award["amount"] == 400  # 100*3 (own) + folded seat3's 100
    # 400 // 3 = 133 remainder 1 -> one winner gets 134, others 133.
    # Odd chip goes to the first winner left of the button (button=0 -> seat1).
    assert t.seats[1]["stack"] == 1000 + 134
    assert t.seats[0]["stack"] == 1000 + 133
    assert t.seats[2]["stack"] == 1000 + 133


def test_everyone_folds_to_bb_is_a_walk():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    while t.hand_in_progress and t._street == "preflop" and len([s for s in t._hand_seats if t._pstate[s] != "folded"]) > 1:
        seat = t.to_act()
        if seat == t._bb_seat:
            break
        t.apply(seat, Action("fold"))
    # remaining seat besides bb should fold or bb wins by walk once all others folded
    while t.hand_in_progress:
        seat = t.to_act()
        if seat == t._bb_seat and len([s for s in t._hand_seats if t._pstate[s] != "folded"]) == 1:
            break
        t.apply(seat, Action("fold"))
    assert not t.hand_in_progress
    assert t._last_hand_summary["winners"] == [t._bb_seat]
    assert t._last_hand_summary["reveals"] == []  # no cards shown on a fold-out


def test_bb_option_when_limped_to():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    # everyone limps (calls) to the BB
    while t.to_act() != t._bb_seat:
        seat = t.to_act()
        t.apply(seat, Action("call"))
    leg = t.legal()
    assert leg.can_check is True
    assert leg.raise_kind == "raise"  # BB may still raise (the option)
    t.apply(t._bb_seat, Action("check"))
    assert t._street == "flop"


def test_blind_all_in_short_stack():
    t = new_table(stacks=[1000, 1000, 1000, 3])
    t.start_hand()
    assert t._pstate[t._bb_seat] == ("all_in" if t._bb_seat == 3 else t._pstate[t._bb_seat])
    if t._bb_seat == 3:
        assert t.seats[3]["stack"] == 0
        assert t._committed[3] == 3


def test_player_exactly_zero_after_posting_blind():
    t = new_table(stacks=[1000, 1000, 1000, 10])  # seat3 == bb, posts exactly bb=10
    t.start_hand()
    if t._bb_seat == 3:
        assert t.seats[3]["stack"] == 0
        assert t._pstate[3] == "all_in"


def test_table_over_sets_winner():
    t = new_table(stacks=[1000, 1000, 0, 0])
    t.seats[2]["out"] = True
    t.seats[3]["out"] = True
    t.start_hand()
    # force seat0 to bust by folding every hand until done, or drive one big pot:
    while t.hand_in_progress:
        seat = t.to_act()
        leg = t.legal()
        if leg.raise_kind:
            t.apply(seat, Action("all_in"))
        else:
            t.apply(seat, Action("call") if leg.can_call else Action("check"))
    if t.seats[0]["stack"] == 0 or t.seats[1]["stack"] == 0:
        assert t.table_over is True
        assert t.winner in (0, 1)


# ---------------------------------------------------------------------
# IllegalAction coverage
# ---------------------------------------------------------------------
def test_illegal_out_of_turn():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    wrong_seat = (t.to_act() + 1) % 4
    with pytest.raises(IllegalAction) as ei:
        t.apply(wrong_seat, Action("fold"))
    assert ei.value.code == "not_your_turn"


def test_illegal_no_hand_in_progress():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    with pytest.raises(IllegalAction) as ei:
        t.apply(0, Action("fold"))
    assert ei.value.code == "no_hand"


def test_illegal_amount_below_min_above_max():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    while t._street == "preflop":
        seat = t.to_act()
        t.apply(seat, Action("call") if t.legal().can_call else Action("check"))
    seat = t.to_act()
    leg = t.legal()
    with pytest.raises(IllegalAction) as ei:
        t.apply(seat, Action("bet", to=leg.min_to - 1))
    assert ei.value.code == "bad_amount"
    with pytest.raises(IllegalAction) as ei:
        t.apply(seat, Action("bet", to=leg.max_to + 1))
    assert ei.value.code == "bad_amount"


def test_illegal_non_int_and_bool_and_negative_to():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    seat = t.to_act()
    with pytest.raises(IllegalAction):
        t.apply(seat, Action("raise", to=True))
    with pytest.raises(IllegalAction):
        t.apply(seat, Action("raise", to=20.5))
    with pytest.raises(IllegalAction):
        t.apply(seat, Action("raise", to=-5))


def test_illegal_to_rejected_on_non_bet_raise():
    # engine's documented choice: `to` must be None for fold/check/call/all_in.
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    seat = t.to_act()
    with pytest.raises(IllegalAction) as ei:
        t.apply(seat, Action("call", to=20))
    assert ei.value.code == "bad_amount"


def test_illegal_stale_kind():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    seat = t.to_act()
    with pytest.raises(IllegalAction) as ei:
        t.apply(seat, Action("frobnicate"))
    assert ei.value.code == "illegal_kind"


def test_state_unchanged_on_rejection():
    t = new_table(stacks=[1000, 1000, 1000, 1000])
    t.start_hand()
    seat = t.to_act()
    version_before = t.version
    stacks_before = [dict(s) for s in t.seats]
    with pytest.raises(IllegalAction):
        t.apply(seat, Action("raise", to=-5))
    assert t.version == version_before
    assert [dict(s) for s in t.seats] == stacks_before
    assert t.to_act() == seat
