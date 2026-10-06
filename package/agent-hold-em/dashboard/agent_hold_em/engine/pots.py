"""Side-pot construction from total per-seat contributions.

Pure function, no engine dependencies — used by the real engine and
independently re-derived (NOT imported) by the pot-settlement oracle in
tests/engine/test_pot_oracle.py for cross-checking.
"""


def build_side_pots(contrib, folded):
    """Build layered side pots from total contributions.

    contrib: {seat: total_chips_contributed_this_hand} for every seat that
             put in any chips (folded or not).
    folded:  set of seats that folded (ineligible to win any pot, but their
             chips still fund pots they contributed to).

    Returns a list of {"amount": int, "eligible": [seat, ...]} in ascending
    layer order (main pot first, side pots after), skipping zero-amount
    layers. `eligible` seats are sorted ascending by seat number.
    """
    contributors = [s for s, amt in contrib.items() if amt > 0]
    if not contributors:
        return []
    levels = sorted(set(contrib[s] for s in contributors))
    pots = []
    prev = 0
    for level in levels:
        layer_size = level - prev
        if layer_size <= 0:
            prev = level
            continue
        payers = [s for s in contributors if contrib[s] >= level]
        amount = layer_size * len(payers)
        eligible = sorted(s for s in payers if s not in folded)
        if amount > 0:
            pots.append({"amount": amount, "eligible": eligible})
        prev = level
    return pots
