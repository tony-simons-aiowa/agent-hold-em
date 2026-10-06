"""Per-seat public stats, derived only from PUBLIC action events.

hands: hands dealt to that seat.
vpip:  fraction of hands where the seat voluntarily put chips in preflop
       (any call/bet/raise/all_in preflop; posting a blind does not count).
pfr:   fraction of hands where the seat bet or raised preflop.
af:    aggression factor = (bets+raises) / calls, across all streets, all
       time (not per-hand). None (reported as 0.0) when calls == 0.
"""


class SeatStats:
    __slots__ = (
        "hands", "vpip_hands", "pfr_hands", "bets_raises", "calls",
        "_vpip_this_hand", "_pfr_this_hand",
    )

    def __init__(self):
        self.hands = 0
        self.vpip_hands = 0
        self.pfr_hands = 0
        self.bets_raises = 0
        self.calls = 0
        self._vpip_this_hand = False
        self._pfr_this_hand = False

    def to_dict(self):
        af = (self.bets_raises / self.calls) if self.calls else 0.0
        vpip = (self.vpip_hands / self.hands) if self.hands else 0.0
        pfr = (self.pfr_hands / self.hands) if self.hands else 0.0
        return {"hands": self.hands, "vpip": vpip, "pfr": pfr, "af": af}

    def to_state(self):
        return {
            "hands": self.hands,
            "vpip_hands": self.vpip_hands,
            "pfr_hands": self.pfr_hands,
            "bets_raises": self.bets_raises,
            "calls": self.calls,
            "vpip_this_hand": self._vpip_this_hand,
            "pfr_this_hand": self._pfr_this_hand,
        }

    @staticmethod
    def from_state(d):
        s = SeatStats()
        s.hands = d.get("hands", 0)
        s.vpip_hands = d.get("vpip_hands", 0)
        s.pfr_hands = d.get("pfr_hands", 0)
        s.bets_raises = d.get("bets_raises", 0)
        s.calls = d.get("calls", 0)
        s._vpip_this_hand = d.get("vpip_this_hand", False)
        s._pfr_this_hand = d.get("pfr_this_hand", False)
        return s


class StatsTracker:
    """Owns one SeatStats per seat and updates from the public event stream."""

    def __init__(self, num_seats):
        self.by_seat = {s: SeatStats() for s in range(num_seats)}

    def to_state(self):
        return {str(s): st.to_state() for s, st in self.by_seat.items()}

    @staticmethod
    def from_state(d, num_seats):
        t = StatsTracker(num_seats)
        for k, v in (d or {}).items():
            t.by_seat[int(k)] = SeatStats.from_state(v)
        return t

    def on_hand_start(self, seats_dealt):
        for s in seats_dealt:
            st = self.by_seat[s]
            st.hands += 1
            st._vpip_this_hand = False
            st._pfr_this_hand = False

    def on_action(self, seat, kind, street):
        st = self.by_seat.get(seat)
        if st is None:
            return
        if kind in ("bet", "raise", "all_in"):
            # an all_in that is really just a call-for-less is still,
            # conservatively, counted as aggression only when it increased
            # the street's current bet; callers pass the resolved kind.
            st.bets_raises += 1
            if street == "preflop":
                st._vpip_this_hand = True
                st._pfr_this_hand = True
        elif kind == "call":
            st.calls += 1
            if street == "preflop":
                st._vpip_this_hand = True

    def on_hand_end(self):
        for st in self.by_seat.values():
            if st._vpip_this_hand:
                st.vpip_hands += 1
            if st._pfr_this_hand:
                st.pfr_hands += 1

    def snapshot(self, seat):
        return self.by_seat[seat].to_dict()
