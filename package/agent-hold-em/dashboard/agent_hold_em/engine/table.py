"""Table — the authoritative multi-hand No-Limit Hold 'Em state machine.

See docs/ARCHITECTURE.md §3 for the binding interface and docs/TESTING.md
for documented rule decisions (button/blind rotation, reveal rule, odd-chip
rule, incomplete-raise/reopen rule, uncalled-bet-return timing).
"""
from .cards import parse_card
from .deck import secure_deck
from .errors import IllegalAction
from .evaluator import evaluate_seven, hand_label
from .hand import STREET_ORDER
from .legal import Action, Legal
from .pots import build_side_pots
from .stats import StatsTracker
from . import views

NUM_SEATS = 4


class Table:
    # ---------------------------------------------------------------
    # Construction
    # ---------------------------------------------------------------
    def __init__(self, names, stack, sb, bb, deck_factory):
        if len(names) != NUM_SEATS:
            raise ValueError(f"Table requires exactly {NUM_SEATS} seat names")
        self.seats = [{"name": n, "stack": int(stack), "out": False} for n in names]
        self.sb = int(sb)
        self.bb = int(bb)
        self.deck_factory = deck_factory

        self.button = -1
        self.hand_no = 0
        self.version = 0
        self.hand_in_progress = False
        self.table_over = False
        self.winner = None

        self._completed_hands = []
        self._stats = StatsTracker(NUM_SEATS)
        self._last_hand_summary = None
        self._pending = []

        self._hand_seats = None
        self._hole = {}
        self._board = []
        self._burns = []
        self._deck = []
        self._committed = {}
        self._total_in_pot = {}
        self._pstate = {}
        self._acted = {}
        self._can_raise = {}
        self._last_action = {}
        self._current_bet = 0
        self._last_full_raise_size = self.bb
        self._baseline = 0
        self._street = None
        self._sb_seat = None
        self._bb_seat = None
        self._heads_up = False
        self._to_act = None
        self._last_actor = None
        self._current_hand_log = []

    @staticmethod
    def new(names, *, stack=1000, sb=5, bb=10, deck_factory=secure_deck):
        return Table(list(names), stack, sb, bb, deck_factory)

    # ---------------------------------------------------------------
    # Small helpers
    # ---------------------------------------------------------------
    def _seats_with_chips(self):
        return [s for s in range(NUM_SEATS) if (not self.seats[s]["out"]) and self.seats[s]["stack"] > 0]

    @staticmethod
    def _cycle_from(start, n=NUM_SEATS):
        return [(start + i) % n for i in range(n)]

    def _emit(self, ev):
        ev = dict(ev)
        ev.setdefault("hand_no", self.hand_no)
        self._pending.append(ev)
        self._current_hand_log.append(ev)

    def _active_seats(self):
        return [s for s in self._hand_seats if self._pstate[s] == "active"]

    def _round_closed(self):
        for s in self._active_seats():
            if not (self._acted[s] and self._committed[s] == self._current_bet):
                return False
        return True

    def _scan_next_active(self, pointer):
        i = pointer
        for _ in range(NUM_SEATS):
            i = (i + 1) % NUM_SEATS
            if i in self._hand_seats and self._pstate[i] == "active":
                return i
        return None

    # ---------------------------------------------------------------
    # Hand lifecycle: start_hand
    # ---------------------------------------------------------------
    def start_hand(self):
        if self.table_over:
            raise IllegalAction("table_over", "table is finished")
        if self.hand_in_progress:
            raise IllegalAction("hand_in_progress", "a hand is already in progress")

        seats_wc = self._seats_with_chips()
        if len(seats_wc) < 2:
            self.table_over = True
            self.winner = seats_wc[0] if seats_wc else None
            raise IllegalAction("table_over", "fewer than two players have chips")

        self._pending = []

        new_button = None
        for i in range(1, NUM_SEATS + 1):
            cand = (self.button + i) % NUM_SEATS
            if cand in seats_wc:
                new_button = cand
                break
        self.button = new_button

        hand_seats = [s for s in self._cycle_from(self.button + 1) if s in seats_wc]
        self._hand_seats = hand_seats
        self.hand_no += 1
        self._current_hand_log = []
        self._board = []
        self._burns = []
        self._deck = self.deck_factory()
        self._hole = {s: [] for s in hand_seats}
        self._committed = {s: 0 for s in range(NUM_SEATS)}
        self._total_in_pot = {s: 0 for s in range(NUM_SEATS)}
        self._pstate = {s: ("active" if s in hand_seats else "out") for s in range(NUM_SEATS)}
        self._acted = {s: False for s in range(NUM_SEATS)}
        self._can_raise = {s: True for s in range(NUM_SEATS)}
        self._last_action = {s: None for s in range(NUM_SEATS)}
        self._street = "preflop"

        heads_up = len(hand_seats) == 2
        self._heads_up = heads_up
        if heads_up:
            sb_seat = self.button
            bb_seat = [s for s in hand_seats if s != self.button][0]
        else:
            sb_seat = hand_seats[0]
            bb_seat = hand_seats[1]
        self._sb_seat = sb_seat
        self._bb_seat = bb_seat

        def post(seat, amt):
            stack = self.seats[seat]["stack"]
            pay = min(amt, stack)
            self.seats[seat]["stack"] -= pay
            self._committed[seat] += pay
            if self.seats[seat]["stack"] == 0:
                self._pstate[seat] = "all_in"
            return pay

        sb_paid = post(sb_seat, self.sb)
        bb_paid = post(bb_seat, self.bb)
        self._current_bet = max(sb_paid, bb_paid)
        self._last_full_raise_size = self.bb
        self._baseline = self._current_bet

        self._emit({"type": "hand_start", "seats": list(hand_seats), "button": self.button})
        self._emit({
            "type": "blinds", "sb_seat": sb_seat, "sb_amount": sb_paid,
            "bb_seat": bb_seat, "bb_amount": bb_paid,
        })

        for _round in range(2):
            for s in hand_seats:
                card = self._deck.pop(0)
                self._hole[s].append(card)
        self._emit({"type": "deal", "seats": list(hand_seats)})

        self._stats.on_hand_start(hand_seats)
        self.hand_in_progress = True
        self._last_actor = bb_seat
        self._to_act = None
        self._advance()
        self.version += 1
        return list(self._pending)

    # ---------------------------------------------------------------
    # Query surface
    # ---------------------------------------------------------------
    def to_act(self):
        if not self.hand_in_progress:
            return None
        return self._to_act

    def _compute_legal(self, seat):
        current_bet = self._current_bet
        committed = self._committed[seat]
        stack = self.seats[seat]["stack"]
        to_call = max(0, current_bet - committed)
        all_in_to = committed + stack
        can_check = to_call == 0
        can_call = to_call > 0
        call_amount = min(to_call, stack)

        can_raise_flag = self._can_raise[seat] and stack > 0 and all_in_to > current_bet
        if not can_raise_flag:
            raise_kind = None
            min_to = None
            max_to = None
        else:
            raise_kind = "bet" if current_bet == 0 else "raise"
            min_to_natural = self._baseline + self._last_full_raise_size
            min_to = min(min_to_natural, all_in_to)
            max_to = all_in_to

        return Legal(
            seat=seat, to_call=to_call, can_fold=True, can_check=can_check,
            can_call=can_call, call_amount=call_amount, raise_kind=raise_kind,
            min_to=min_to, max_to=max_to, all_in_to=all_in_to, stack=stack,
            current_bet=current_bet, committed=committed,
        )

    def legal(self):
        if not self.hand_in_progress or self._to_act is None:
            return None
        return self._compute_legal(self._to_act)

    def legal_for_display(self, seat):
        """Convenience: legal() for an arbitrary seat, even if not to_act.

        NOT the source of truth for whether an action will be accepted —
        `legal()` (for the seat currently to_act) and `apply()`'s own
        validation are authoritative.
        """
        if not self.hand_in_progress:
            return None
        return self._compute_legal(seat)

    # ---------------------------------------------------------------
    # apply()
    # ---------------------------------------------------------------
    def apply(self, seat, action):
        if not self.hand_in_progress:
            raise IllegalAction("no_hand", "no hand in progress")
        if seat != self._to_act:
            raise IllegalAction("not_your_turn", f"seat {seat} is not to act")

        kind = action.kind
        to = action.to
        if kind not in ("fold", "check", "call", "bet", "raise", "all_in"):
            raise IllegalAction("illegal_kind", f"unknown action kind {kind!r}")

        if kind in ("bet", "raise"):
            if to is None or isinstance(to, bool) or not isinstance(to, int):
                raise IllegalAction("bad_amount", "to must be an int for bet/raise")
        else:
            if to is not None:
                raise IllegalAction("bad_amount", f"to must be None for {kind}")

        legal = self._compute_legal(seat)
        self._pending = []
        fallback = bool(action.fallback)

        if kind == "fold":
            self._do_fold(seat, fallback)
        elif kind == "check":
            if not legal.can_check:
                raise IllegalAction("illegal_kind", "check not legal; must call, raise or fold")
            self._do_check(seat, fallback)
        elif kind == "call":
            if legal.to_call == 0:
                self._do_check(seat, fallback)  # tolerant: call with nothing to call == check
            else:
                self._do_call(seat, fallback, "call")
        elif kind in ("bet", "raise"):
            if legal.raise_kind is None:
                raise IllegalAction("illegal_kind", "betting is not reopened for this seat; only call or fold")
            if kind != legal.raise_kind:
                raise IllegalAction("illegal_kind", f"use {legal.raise_kind!r}, not {kind!r}, here")
            if to < legal.min_to or to > legal.max_to:
                raise IllegalAction("bad_amount", f"to must be between {legal.min_to} and {legal.max_to}")
            self._do_raise(seat, to, fallback, kind)
        elif kind == "all_in":
            all_in_to = legal.all_in_to
            if all_in_to <= legal.current_bet:
                self._do_call(seat, fallback, "all_in")
            else:
                if legal.raise_kind is None:
                    raise IllegalAction("illegal_kind", "betting is not reopened for this seat; only call or fold")
                self._do_raise(seat, all_in_to, fallback, "all_in")

        self._last_actor = seat
        self._advance()
        self.version += 1
        return list(self._pending)

    # -- action mutators (each assumes the action already validated) ----
    def _do_fold(self, seat, fallback):
        self._pstate[seat] = "folded"
        self._acted[seat] = True
        self._last_action[seat] = {"kind": "fold", "to": None, "fallback": fallback}
        self._emit({"type": "action", "seat": seat, "kind": "fold", "to": None, "amount_added": 0})

    def _do_check(self, seat, fallback):
        self._acted[seat] = True
        to_val = self._committed[seat]
        self._last_action[seat] = {"kind": "check", "to": to_val, "fallback": fallback}
        self._emit({"type": "action", "seat": seat, "kind": "check", "to": to_val, "amount_added": 0})

    def _do_call(self, seat, fallback, reported_kind):
        to_call = self._current_bet - self._committed[seat]
        stack = self.seats[seat]["stack"]
        add = max(0, min(to_call, stack))
        self.seats[seat]["stack"] -= add
        self._committed[seat] += add
        if self.seats[seat]["stack"] == 0:
            self._pstate[seat] = "all_in"
        self._acted[seat] = True
        self._stats.on_action(seat, "call", self._street)
        self._last_action[seat] = {"kind": reported_kind, "to": self._committed[seat], "fallback": fallback}
        self._emit({
            "type": "action", "seat": seat, "kind": reported_kind,
            "to": self._committed[seat], "amount_added": add,
        })

    def _do_raise(self, seat, to_amount, fallback, reported_kind):
        old_committed = self._committed[seat]
        add = to_amount - old_committed
        self.seats[seat]["stack"] -= add
        self._committed[seat] = to_amount
        if self.seats[seat]["stack"] == 0:
            self._pstate[seat] = "all_in"

        delta = to_amount - self._baseline
        is_full = delta >= self._last_full_raise_size
        if is_full:
            self._baseline = to_amount
            self._last_full_raise_size = delta
            self._current_bet = to_amount
            for s in self._active_seats():
                if s != seat:
                    self._acted[s] = False
                    self._can_raise[s] = True
        else:
            self._current_bet = to_amount
            for s in self._active_seats():
                if s != seat and self._acted[s]:
                    self._can_raise[s] = False

        self._acted[seat] = True
        self._stats.on_action(seat, "bet", self._street)
        self._last_action[seat] = {"kind": reported_kind, "to": to_amount, "fallback": fallback}
        self._emit({
            "type": "action", "seat": seat, "kind": reported_kind,
            "to": to_amount, "amount_added": add,
        })

    # ---------------------------------------------------------------
    # Street / hand advancement
    # ---------------------------------------------------------------
    def _advance(self):
        while True:
            non_folded = [s for s in self._hand_seats if self._pstate[s] != "folded"]
            if len(non_folded) == 1:
                self._settle_fold_win(non_folded[0])
                return
            if not self._round_closed():
                self._to_act = self._scan_next_active(self._last_actor)
                return
            if self._street == "river":
                self._settle_showdown()
                return
            self._advance_street()

    def _advance_street(self):
        for s in self._hand_seats:
            self._total_in_pot[s] += self._committed[s]
            self._committed[s] = 0

        idx = STREET_ORDER.index(self._street)
        nxt = STREET_ORDER[idx + 1]

        self._burns.append(self._deck.pop(0))
        if nxt == "flop":
            for _ in range(3):
                self._board.append(self._deck.pop(0))
        else:
            self._board.append(self._deck.pop(0))

        self._street = nxt
        self._current_bet = 0
        self._last_full_raise_size = self.bb
        self._baseline = 0
        for s in self._hand_seats:
            if self._pstate[s] == "active":
                self._acted[s] = False
                self._can_raise[s] = True

        self._emit({"type": "street", "name": nxt, "board": list(self._board)})
        self._last_actor = self.button

    # ---------------------------------------------------------------
    # Settlement
    # ---------------------------------------------------------------
    def _finalize_contributions(self):
        for s in self._hand_seats:
            self._total_in_pot[s] += self._committed[s]
            self._committed[s] = 0

    def _apply_uncalled_return(self):
        contributed = {s: self._total_in_pot[s] for s in self._hand_seats if self._total_in_pot[s] > 0}
        if not contributed:
            return
        top_seat = max(contributed, key=lambda s: contributed[s])
        top_amt = contributed[top_seat]
        others = [amt for s, amt in contributed.items() if s != top_seat]
        second = max(others) if others else 0
        excess = top_amt - second
        if excess > 0:
            self._total_in_pot[top_seat] -= excess
            self.seats[top_seat]["stack"] += excess
            self._emit({"type": "uncalled_return", "seat": top_seat, "amount": excess})

    def _settle_fold_win(self, winner):
        self._finalize_contributions()
        self._apply_uncalled_return()
        total = sum(self._total_in_pot[s] for s in self._hand_seats)
        self.seats[winner]["stack"] += total
        award = {"pot_index": 0, "amount": total, "winners": [winner], "split": False}
        self._emit({"type": "pot_award", **award})
        self._last_hand_summary = {
            "hand_no": self.hand_no, "winners": [winner],
            "pot_awards": [award], "reveals": [],
        }
        self._end_hand_common()

    def _build_pots_for_showdown(self, folded):
        non_folded = [s for s in self._hand_seats if s not in folded]
        contributed_all = {s: self._total_in_pot[s] for s in self._hand_seats if self._total_in_pot[s] > 0}
        max_nonfolded = max((self._total_in_pot[s] for s in non_folded), default=0)
        adjusted = {}
        leftover = 0
        for s, amt in contributed_all.items():
            if s in folded and amt > max_nonfolded:
                leftover += amt - max_nonfolded
                adjusted[s] = max_nonfolded
            else:
                adjusted[s] = amt
        pots = build_side_pots(adjusted, folded)
        if leftover and pots:
            pots[-1]["amount"] += leftover
        return pots

    def _settle_showdown(self):
        self._finalize_contributions()
        self._apply_uncalled_return()
        folded = {s for s in self._hand_seats if self._pstate[s] == "folded"}
        non_folded = [s for s in self._hand_seats if s not in folded]

        keys = {}
        reveals = []
        for s in non_folded:
            cards7 = list(self._hole[s]) + list(self._board)
            key, _best5 = evaluate_seven(cards7)
            keys[s] = key
            reveals.append({"seat": s, "cards": list(self._hole[s]), "hand_label": hand_label(key)})
        self._emit({"type": "showdown", "reveals": reveals})

        pots = self._build_pots_for_showdown(folded)
        pot_awards = []
        for idx, pot in enumerate(pots):
            elig = pot["eligible"]
            amount = pot["amount"]
            if not elig:
                continue
            best = max(keys[s] for s in elig)
            winners = [s for s in elig if keys[s] == best]
            base = amount // len(winners)
            rem = amount - base * len(winners)
            order = [s for s in self._cycle_from(self.button + 1) if s in winners]
            extra = set()
            for i in range(rem):
                extra.add(order[i % len(order)])
            for w in winners:
                self.seats[w]["stack"] += base + (1 if w in extra else 0)
            award = {"pot_index": idx, "amount": amount, "winners": winners, "split": len(winners) > 1}
            pot_awards.append(award)
            self._emit({"type": "pot_award", **award})

        all_winners = sorted(set(w for pa in pot_awards for w in pa["winners"]))
        self._last_hand_summary = {
            "hand_no": self.hand_no, "winners": all_winners,
            "pot_awards": pot_awards, "reveals": reveals,
        }
        self._end_hand_common()

    def _end_hand_common(self):
        self._stats.on_hand_end()
        self._emit({"type": "hand_end"})
        for s in self._hand_seats:
            if self.seats[s]["stack"] == 0 and not self.seats[s]["out"]:
                self.seats[s]["out"] = True
                self._emit({"type": "bust", "seat": s})

        self.hand_in_progress = False
        self._to_act = None

        record = {"hand_no": self.hand_no, "events": list(self._current_hand_log)}
        self._completed_hands.append(record)
        if len(self._completed_hands) > 200:
            self._completed_hands = self._completed_hands[-200:]

        seats_wc = self._seats_with_chips()
        if len(seats_wc) <= 1:
            self.table_over = True
            self.winner = seats_wc[0] if seats_wc else None
            self._emit({"type": "table_over", "winner": self.winner})

    # ---------------------------------------------------------------
    # Views / history
    # ---------------------------------------------------------------
    def view(self, viewer=None):
        return views.build_view(self, viewer)

    def public_history(self):
        return views.build_public_history(self)

    # ---------------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------------
    SCHEMA = 1

    @staticmethod
    def _strkeys(d):
        return {str(k): v for k, v in d.items()}

    @staticmethod
    def _intkeys(d):
        return {int(k): v for k, v in d.items()}

    def to_dict(self):
        hand_state = None
        if self._hand_seats is not None:
            hand_state = {
                "hand_seats": list(self._hand_seats),
                "hole": self._strkeys(self._hole),
                "board": list(self._board),
                "burns": list(self._burns),
                "remaining_deck": list(self._deck),
                "committed": self._strkeys(self._committed),
                "total_in_pot": self._strkeys(self._total_in_pot),
                "pstate": self._strkeys(self._pstate),
                "acted": self._strkeys(self._acted),
                "can_raise": self._strkeys(self._can_raise),
                "last_action": self._strkeys(self._last_action),
                "current_bet": self._current_bet,
                "last_full_raise_size": self._last_full_raise_size,
                "baseline": self._baseline,
                "street": self._street,
                "sb_seat": self._sb_seat,
                "bb_seat": self._bb_seat,
                "heads_up": self._heads_up,
                "to_act": self._to_act,
                "last_actor": self._last_actor,
                "current_hand_log": list(self._current_hand_log),
            }
        return {
            "schema": self.SCHEMA,
            "seats": [dict(s) for s in self.seats],
            "button": self.button,
            "hand_no": self.hand_no,
            "version": self.version,
            "hand_in_progress": self.hand_in_progress,
            "table_over": self.table_over,
            "winner": self.winner,
            "sb": self.sb,
            "bb": self.bb,
            "completed_hands": self._completed_hands,
            "stats": self._stats.to_state(),
            "last_hand_summary": self._last_hand_summary,
            "hand_state": hand_state,
        }

    @staticmethod
    def from_dict(d, deck_factory=secure_deck):
        if d.get("schema") != Table.SCHEMA:
            raise ValueError(f"unsupported table schema {d.get('schema')!r}")
        t = Table.__new__(Table)
        t.sb = d["sb"]
        t.bb = d["bb"]
        t.deck_factory = deck_factory
        t.seats = [dict(s) for s in d["seats"]]
        t.button = d["button"]
        t.hand_no = d["hand_no"]
        t.version = d["version"]
        t.hand_in_progress = d["hand_in_progress"]
        t.table_over = d["table_over"]
        t.winner = d["winner"]
        t._completed_hands = d["completed_hands"]
        t._stats = StatsTracker.from_state(d["stats"], NUM_SEATS)
        t._last_hand_summary = d.get("last_hand_summary")
        t._pending = []

        hs = d.get("hand_state")
        if hs is None:
            t._hand_seats = None
            t._hole = {}
            t._board = []
            t._burns = []
            t._deck = []
            t._committed = {}
            t._total_in_pot = {}
            t._pstate = {}
            t._acted = {}
            t._can_raise = {}
            t._last_action = {}
            t._current_bet = 0
            t._last_full_raise_size = t.bb
            t._baseline = 0
            t._street = None
            t._sb_seat = None
            t._bb_seat = None
            t._heads_up = False
            t._to_act = None
            t._last_actor = None
            t._current_hand_log = []
        else:
            t._hand_seats = list(hs["hand_seats"])
            t._hole = Table._intkeys(hs["hole"])
            t._board = list(hs["board"])
            t._burns = list(hs["burns"])
            t._deck = list(hs["remaining_deck"])
            t._committed = Table._intkeys(hs["committed"])
            t._total_in_pot = Table._intkeys(hs["total_in_pot"])
            t._pstate = Table._intkeys(hs["pstate"])
            t._acted = Table._intkeys(hs["acted"])
            t._can_raise = Table._intkeys(hs["can_raise"])
            t._last_action = Table._intkeys(hs["last_action"])
            t._current_bet = hs["current_bet"]
            t._last_full_raise_size = hs["last_full_raise_size"]
            t._baseline = hs["baseline"]
            t._street = hs["street"]
            t._sb_seat = hs["sb_seat"]
            t._bb_seat = hs["bb_seat"]
            t._heads_up = hs["heads_up"]
            t._to_act = hs["to_act"]
            t._last_actor = hs["last_actor"]
            t._current_hand_log = list(hs["current_hand_log"])
        return t
