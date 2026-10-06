# Testing — Engine

This section covers `package/agent-hold-em/dashboard/agent_hold_em/engine/`
and `tests/engine/`. Other components add their own sections to this file;
do not remove theirs when adding to this one.

## Running

```bash
cd agent-hold-em && . scripts/env.sh

# fast tests only (~4s, what you run while iterating)
$PY -m pytest tests/engine -m "not slow" -q

# everything, including the exhaustive evaluator enumeration and the
# 5,000+ hand simulation/privacy sweeps (~55s)
$PY -m pytest tests/engine -q
```

`tests/engine/conftest.py` puts `package/agent-hold-em/dashboard` on
`sys.path` directly, so these tests also run standalone with any CPython
3.11+ that has `pytest` — they do not need Hermes on the path (the engine
itself is stdlib-only). `scripts/env.sh` is still the supported/canonical
way to run them, matching the exact interpreter `hermes serve` uses.

## Documented rule decisions

- **Button/blind rotation**: "simple moving button" — the button moves to
  the next seat that still has chips (a busted seat is skipped forever).
  3–4 handed: SB = next live seat after the button, BB = next live seat
  after SB. **Heads-up** (exactly 2 live players): the button posts the
  SB and acts first preflop; the other seat is BB and acts first on every
  postflop street. A seat that can't cover its blind posts all-in for
  whatever it has; `last_full_raise_size` for the street is still the
  nominal big blind regardless of a short blind post.
- **Preflop/postflop first-to-act**: implemented as one uniform rule —
  preflop, action starts on the next active seat found scanning forward
  from the BB seat (which, in heads-up, lands back on the button/SB,
  automatically giving the correct heads-up order without a special
  case); postflop, scanning starts from the button. See `Table._scan_next_active`.
- **Incomplete (short all-in) raise reopening**: the **TDA cumulative
  rule** is implemented, not the simpler independent-incomplete-raise
  rule. `Table` tracks `_baseline` (the street's current bet at the point
  of the last *full* raise) and `_last_full_raise_size`. A raise to `to`
  is full iff `to - baseline >= last_full_raise_size`; a full raise resets
  `baseline = to`, `last_full_raise_size = to - old_baseline`, and
  re-opens action (`acted=False`, `can_raise=True`) for every other active
  seat. An incomplete raise (necessarily an all-in, since a voluntary
  raise is always bounded below by `min_to`) only raises `current_bet`
  (so seats who already matched must act again) and sets `can_raise=False`
  for seats that had **already acted since baseline** — but never for
  seats that haven't acted yet this street, who may always still raise
  fully. Because `baseline` doesn't move on an incomplete raise, a second,
  third, … incomplete raise is compared against the *same* baseline, so
  several short all-ins that cumulatively reach a full raise's size do
  reopen action once that cumulative threshold is crossed — exactly the
  scenario in `tests/engine/test_scenarios.py::test_cumulative_incomplete_raises_reopen_tda_rule`.
- **Uncalled bet return**: computed once, at the moment a hand is
  finalized (either "everyone else folds" or full showdown/runout), from
  each seat's *total* hand contribution (all streets folded together via
  `_finalize_contributions`). Comparing final totals rather than doing it
  street-by-street is equivalent and simpler: any street where every
  contribution matched exactly cannot create a gap, so the only gap that
  can ever exist by hand-end is the one from the final unmatched bet —
  which the total-contribution comparison catches correctly regardless of
  which street it happened on.
- **Side pots**: layered from total contributions (`engine/pots.py:
  build_side_pots`), by ascending contribution level; each layer's
  `eligible` winners are its payers minus anyone folded. A folded seat's
  contribution *above* the maximum surviving (non-folded) seat's total is
  not returned to them (folding forfeits it) — it is folded into the
  **top** pot instead of creating a pot with zero eligible winners
  (`Table._build_pots_for_showdown`). This only matters in the rare case
  where a folded seat's total contribution exceeds every remaining
  player's (e.g. a short all-in call capped someone at a lower total than
  a bigger stack that later folded to further action after already
  matching more).
- **Showdown reveal rule**: v1, no mucking — every non-folded seat's hand
  is revealed at showdown, always. If a fold ends the hand early, nobody's
  cards are shown (`reveals: []`), consistent with real play.
- **Split pots / odd chips**: an exact tie divides the pot with integer
  floor division; the remainder is distributed **one chip at a time, to
  the tied winners in seat order starting from the first seat left of the
  button**, cycling if the remainder ever exceeded winner count (it never
  can, since `remainder < num_winners` by construction).
- **`to` must be `None` for fold/check/call/all_in**: chosen over silently
  ignoring a stray `to` — a non-`None` `to` on those kinds raises
  `IllegalAction("bad_amount", …)`. This is the stricter of the two
  options the brief left open; a controller that always follows the
  `Action`/`Legal` contract will never hit it.
- **`call` with `to_call == 0` is treated as `check`**, not rejected —
  mirrors the controller-level tolerant-parsing note in ARCHITECTURE.md
  §4 so the same leniency holds no matter which layer double-checks it.
- **`street` in `view()`** only ever reports `preflop|flop|turn|river` (in
  progress) or `complete` (between hands) — the ARCHITECTURE.md §6 sketch
  also lists `showdown`, but this engine's showdown resolves atomically
  inside the same `apply()` call that closes river betting (no separate
  "awaiting reveal" phase), so there is never a moment where `showdown` is
  the accurate live value; the reveal is visible instead as the
  `showdown` **event** in `log`/`last_hand` the instant it happens.
- **`Action.fallback` (bool, default `False`)** is an additive extension
  beyond the original `Action{kind, to}` sketch in ARCHITECTURE.md §3. It
  lets the service layer's forced check-else-fold fallback (hard rule #8)
  be recorded straight into the engine's own `last_action` view field
  without a second, engine-unaware side channel. It never affects
  legality. ARCHITECTURE.md §3 has been updated accordingly.

## Test files

- **`test_evaluator.py`** — exhaustive enumeration of all C(52,5) =
  2,598,960 five-card hands, asserting category counts match the known
  values exactly (straight flush 40, quads 624, full house 3,744, flush
  5,108, straight 10,200, trips 54,912, two pair 123,552, pair 1,098,240,
  high card 1,302,540); `@pytest.mark.slow` (~7s). Plus (fast): 7-card
  evaluation equals the max of all 21 five-card subsets over 20,000
  random hands; wheel and steel-wheel; flush-vs-straight priority; full
  house from two trips uses the *better* trip; counterfeited two pair;
  board-plays ties; kicker ordering; label-string spot checks for every
  category.
- **`test_pot_oracle.py`** — an **independent** pot-settlement oracle
  (`oracle_payouts`) that does not import `engine.pots`, re-deriving
  uncalled-return + side-pot layering + odd-chip distribution from
  scratch. Cross-checked against the engine's actual `build_side_pots` +
  the same uncalled-return/odd-chip logic over 3,000 randomized scenarios
  (2–4 players, random contributions including 1-chip stacks, random
  folds, forced ties), plus 2,000 pure chip-conservation trials.
- **`test_scenarios.py`** — `fixed_deck`-driven determinism: button/blind
  rotation over 8 hands; button skipping a busted seat; heads-up ordering
  pre/postflop; 4→3→2 handed transition mid-table; min-raise sequences
  (small and large numbers); short all-in that does/doesn't reopen;
  cumulative TDA reopening; call-all-in-for-less; uncalled-bet return
  (big shove vs. small stack); 3-way all-in producing ≥2 side pots; a
  4-way board-plays chop; a directly-driven 3-way split pot verifying the
  exact odd-chip seat assignment; everyone-folds-to-BB walk (no reveal);
  BB option when limped to; blind-forces-all-in and exactly-zero-after-blind;
  table-over + winner; and `IllegalAction` coverage (out-of-turn, no hand
  in progress, amount below min/above max, non-int/bool/negative `to`,
  `to` rejected on non-bet/raise kinds, unknown kind, state unchanged on
  rejection).
- **`test_simulation.py`** — `@pytest.mark.slow`: drives ≥5,000 randomized
  full hands (many all-ins) to completion across many tables, asserting
  after **every** action: chip conservation (stacks + committed +
  total_in_pot == 4,000), no negative stacks, exactly 52 unique cards
  across hole+board+burns+remaining deck, correct board size per street,
  `to_act` always a live non-all-in seat, `legal()` bounds self-consistent
  (`min_to <= max_to`, `all_in_to == committed + stack`), `version`
  strictly increasing, and — at a random point in ~20% of tables — a
  `to_dict()`/`from_dict()` round trip producing an identical `view()` for
  every viewer and identical subsequent play when both copies are driven
  with the same RNG stream. A fast (non-slow) companion test reports
  1,000-hand throughput for the performance note below.
- **`test_privacy.py`** — `@pytest.mark.slow`: serializes `view(viewer)`
  for every viewer plus the current hand's public log across ~3,000
  simulated hands and asserts no forbidden card token (another seat's
  unrevealed hole card, any undealt deck card, any burn card) ever
  appears, using boundary-aware token matching (`2s` must not match
  inside a longer token). Checks are deliberately scoped to the
  **current** hand only: a bare card token recurs every hand (52 cards
  reshuffled from scratch each time), so an older hand's legitimately
  revealed card colliding, as a string, with a *different* card privately
  held in the new hand would otherwise be flagged as a false leak. Also:
  a folded seat's hole cards never appear anywhere in `public_history()`,
  and `to_dict()` (which legitimately holds the deck for recovery) is
  confirmed disjoint from what any `view()` exposes.

## Results (last full run)

- `pytest tests/engine -m "not slow"`: **3,041 passed** in ~4s.
- `pytest tests/engine -m "slow"`: **3 passed** in ~51s (exhaustive
  evaluator ~7s, privacy sweep ~43s, simulation ~1s).
- Full suite: **3,044 passed**, 0 failed, in ~55s.
- Performance: 1,000 simulated hands (random legal actions incl. many
  all-ins, across as many tables as needed to reach 1,000 total hands)
  completed in **~0.15s** (~6,700 hands/s) in Hermes' CPython 3.11.16.
  The 5-card evaluator itself runs the full 2,598,960-hand enumeration at
  roughly 370k evals/s; 7-card evaluation (21 five-card subsets via
  `itertools.combinations`, no bit-trick shortcuts) measured at roughly
  8,000 hands/s in the random cross-check — below the "50k/s is plenty"
  guidance, but showdowns are a small fraction of total actions, so
  end-to-end hand throughput is unaffected (6,700 *hands*/s above already
  includes every showdown). If 7-card throughput ever becomes a
  bottleneck, `evaluate_seven` is the single, isolated place to swap in a
  precomputed-rank/bit-trick approach without touching any other module.

# Testing — Service / API (Component C)

Covers `agent_hold_em/service.py`, `agent_hold_em/store.py`, `dashboard/plugin_api.py`
and `tests/service/`, `tests/api/`.

## Running

```bash
cd agent-hold-em && . scripts/env.sh

$PY -m pytest tests/service -m "not integration" -q   # fast (~20s)
$PY -m pytest tests/api -q                            # fast (~8s)
$PY -m pytest tests/service tests/api -q               # includes the real-AIAgent e2e test (~30s)
scripts/test.sh            # everything above, fast marks only, + frontend build check
scripts/test.sh --slow     # + exhaustive engine sweeps + the real-AIAgent integration tests
```

`tests/service/conftest.py` / `tests/api/conftest.py` put the dashboard package on
`sys.path` and, critically, give every test its **own** scratch `HERMES_HOME`
(`tmp_path`) and reset the process-wide singleton registry (stashed on the `threading`
module — see "Singleton guard" below) so tests never see each other's persisted
`table.json` or `TableService` instance.

## Key technique: `InlineExecutor`

`TableService` always calls `self._executor.submit(...)` while already holding its own
`threading.RLock` (reentrant). Tests inject an `InlineExecutor` whose `submit()` runs the
callable synchronously, on the caller's thread — which re-acquires the same RLock and
just works, since `RLock` is reentrant. This makes every decision path deterministic and
instant: no real thread-scheduling races to flake on, and a whole run of many hands
(chip-conservation and privacy sweeps) completes in a couple of seconds. Real
timing-dependent behavior (`FakeSeatRunner` "latency"/"error" modes) still uses small,
real, bounded sleeps (tens of milliseconds), which is what keeps the suite both
deterministic in outcome and fast in wall-clock time. This is a deliberate
simplification versus a fully fake/injectable clock for `threading.Timer`-driven
deadlines and hand-end delays: those still fire on real wall-clock time, so any test
that depends on one uses small `decision_timeout_s`/`next_hand_delay_s` values (or, for
the hand-end delay specifically, calls `next_hand()` directly to skip the wait, exactly
as the real `/next-hand` endpoint does).

## Documented rule decisions / simplifications

- **`_agent_observation` / privacy leak scans exclude `log` and `last_hand`** when
  checking a *specific* hand's private cards against a *different* hand's observation —
  exactly the "recurring card token" trap `docs/TESTING.md`'s engine section documents:
  `log` and `last_hand` legitimately carry the **previous** hand's revealed cards (a
  different shuffle), so a bare token can coincidentally collide with a different,
  privately-held card in the **current** hand without being a real leak. The scan still
  covers every other field (`board`, `seats[].hole`, `pots`, and the full observation
  passed to `SeatRunner.decide()`), which only ever describe the current hand.
- **Deadline enforcement is two-layered on purpose**: `SeatRunner.decide()` already
  self-bounds by `req.deadline_s` (`HermesSeatRunner`/`FakeSeatRunner` both honor it) and
  returns a `status` the completion handler maps straight to a fallback reason; a
  `threading.Timer` deadline **safety net** (`deadline_s + 3s`) is a belt-and-suspenders
  backstop that forces the same fallback path if a runner ever failed to self-bound. Both
  paths converge on the same `_on_decision` completion handler, which re-validates the
  full binding `(table_id, hand_no, seat, turn_id, state_version)` plus generation before
  applying anything — a late result from either path that no longer matches is logged as
  `stale_decision` and discarded, never applied twice.
- **Singleton guard**: the registry lives as an attribute on the `threading` module
  itself (`threading._agent_hold_em_service_registry_v1`), not on `agent_hold_em.service`
  — this is what makes it survive the *service* module being re-imported fresh on a
  hot-reload (`threading` is always the same module object). Constructing a `TableService`
  directly (bypassing `get_service()`) retires whichever instance was previously
  registered: its generation is set to `-1`, its timers are cancelled, its runners are
  closed, and every generation-tagged callback it might still have pending becomes a
  no-op. `tests/service/test_service.py::test_retired_instance_stops_scheduling_new_turns`
  and `::test_second_instance_retires_first` cover this directly.
- **`kind: "test_bot"` seats are refused with a 422 unless `AGENT_HOLD_EM_DEV=1`** is set
  in the server process's environment — checked in `TableService.configure()`, not just
  at the API layer, so nothing that constructs a `TableService` directly can bypass it
  either.

## Results (last full run)

- `pytest tests/service -m "not integration" -q`: **22 passed, 2 skipped** (~22s). The two
  skips are turn-order-dependent human-action tests that only run when the random deal
  happens to make seat 0 first to act preflop — a real (accepted) simplification: the
  service does not expose a seeded-deck hook through `configure()`, so these tests are
  probabilistic rather than deterministic. See "Open risks" in the completion report.
- `pytest tests/service -q` (incl. `integration`): **23 passed, 2 skipped** (~29s).
- `pytest tests/api -q`: **13 passed** (~8s).
- `pytest tests/controller -q` (unchanged by Component C, re-verified after the `cwd=`
  addition to `HermesSeatRunner`): **76 passed** (~5s).
- `pytest tests/engine -m "not slow" -q` (unchanged): **3,041 passed** (~4s).
- `scripts/build-frontend.sh`: bundle builds clean, only the three allowed import
  specifiers present, parses as ESM.
