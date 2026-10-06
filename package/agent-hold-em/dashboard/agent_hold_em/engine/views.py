"""View / observation construction (docs/ARCHITECTURE.md §6 privacy boundary).

Builds the engine-owned portion of HumanView / agent observations. The
service layer overlays its own meta (status, turn_id, agent runtime state,
settings) on top of what this module returns.

Privacy invariant enforced here: hole cards of a seat other than `viewer`
never appear, and the deck order / undealt cards / burn cards never
appear, in any value this module returns.
"""
from .pots import build_side_pots


def _live_pots(table):
    if not table.hand_in_progress:
        return []
    contributed = {}
    for s in table._hand_seats:
        amt = table._total_in_pot.get(s, 0) + table._committed.get(s, 0)
        if amt > 0:
            contributed[s] = amt
    folded = {s for s in table._hand_seats if table._pstate.get(s) == "folded"}
    return build_side_pots(contributed, folded)


def build_view(table, viewer):
    hand_on = table.hand_in_progress
    hand_seats = table._hand_seats or []

    reveal_labels = {}
    if table._last_hand_summary:
        for r in table._last_hand_summary.get("reveals", []):
            reveal_labels[r["seat"]] = r["hand_label"]

    seats_out = []
    for s in range(4):
        base = table.seats[s]
        if hand_on and s in hand_seats:
            state = table._pstate.get(s, "out")
            committed = table._committed.get(s, 0)
            total_in_pot = table._total_in_pot.get(s, 0) + committed
        else:
            state = "out" if base["out"] else "active"
            committed = 0
            total_in_pot = 0

        hole = None
        if hand_on and s in hand_seats and viewer == s:
            hole = list(table._hole.get(s, []))

        seats_out.append({
            "seat": s,
            "name": base["name"],
            "stack": base["stack"],
            "committed": committed,
            "total_in_pot": total_in_pot,
            "state": state,
            "hole": hole,
            "hand_label": reveal_labels.get(s) if not hand_on else None,
            "last_action": table._last_action.get(s),
            "stats": table._stats.snapshot(s),
        })

    pots = _live_pots(table)
    total_pot = sum(p["amount"] for p in pots)

    to_act = table._to_act if hand_on else None
    legal = None
    if hand_on and viewer is not None and to_act == viewer:
        legal = table._compute_legal(viewer).to_dict()

    street = table._street if hand_on else "complete"

    prev_events = []
    if table._completed_hands:
        prev_events = table._completed_hands[-1]["events"]
    log = (prev_events + list(table._current_hand_log))[-40:]

    return {
        "hand_no": table.hand_no,
        "button": table.button,
        "blinds": {"sb": table.sb, "bb": table.bb},
        "street": street,
        "board": list(table._board) if hand_on else [],
        "pots": pots,
        "total_pot": total_pot,
        "sb_seat": table._sb_seat if hand_on else None,
        "bb_seat": table._bb_seat if hand_on else None,
        "to_act": to_act,
        "seats": seats_out,
        "legal": legal,
        "log": log,
        "last_hand": table._last_hand_summary,
    }


def build_public_history(table):
    hist = list(table._completed_hands)
    if table.hand_in_progress:
        hist = hist + [{"hand_no": table.hand_no, "events": list(table._current_hand_log)}]
    return hist
