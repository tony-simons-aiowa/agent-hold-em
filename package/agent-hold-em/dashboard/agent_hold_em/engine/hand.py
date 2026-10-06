"""Hand-lifecycle constants shared by table.py.

Kept as a separate module per docs/ARCHITECTURE.md §2's engine file layout.
The bulk of hand/street/betting-round logic lives in `table.py` (Table is a
single cohesive state machine); this module holds the small pieces that
are naturally standalone constants/helpers rather than Table methods.
"""

STREET_ORDER = ["preflop", "flop", "turn", "river"]

SEAT_STATES = ("active", "folded", "all_in", "out")
