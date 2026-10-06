import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, ConfirmDialog, CopyButton, StatusDot } from '@hermes/plugin-sdk'
import { Seat } from './Seat.jsx'
import { BoardArea } from './Board.jsx'
import { BettingBar } from './BettingBar.jsx'
import { HistoryPanel } from './HistoryPanel.jsx'
import { TableChat } from './TableChat.jsx'
import { newClientActionId } from '../api.js'
import { clamp, fmtChips, opponentSummaryLabel, secondsUntil } from '../format.js'
import { useBettingShortcuts, useNow, usePrefersReducedMotion } from '../hooks.js'

const SLOT_ORDER = ['human', 'left', 'top', 'right']
const DECK_STORAGE_KEY = 'four-color-deck'

/** Assign each seat a felt position, human always bottom-center. */
function layoutSeats(seats, selfSeat) {
  const n = seats.length
  const ordered = []
  for (let i = 0; i < n; i++) {
    ordered.push(seats[(selfSeat + i) % n])
  }
  return ordered.map((seat, i) => ({ seat, slot: SLOT_ORDER[i] ?? `extra-${i}` }))
}

function buildHandSummary(view) {
  // Public-only summary: board, actions and winners come straight from
  // HumanView/log, which never carries another seat's unrevealed hole
  // cards (ARCHITECTURE.md §6) — nothing here reaches into private state.
  const board = view.board?.join(' ') ?? ''
  const winners = view.last_hand?.winners
  const seatsByNo = Object.fromEntries(view.seats.map(s => [s.seat, s.name]))
  const winnerNames = winners?.map(w => seatsByNo[w] ?? `seat ${w}`).join(', ')
  return `Agent Hold 'Em — Hand #${view.last_hand?.hand_no ?? view.hand_no}\nBoard: ${board || '(preflop)'}\nPot: ${fmtChips(
    view.last_hand?.total_pot ?? view.total_pot
  )}${winnerNames ? `\nWinner(s): ${winnerNames}` : ''}`
}

/** Walk the public log backward from the most recent hand_start, collecting
 *  pot_award events, and return {seatNo: chipsAwarded}. Split pots divide the
 *  event's amount evenly across its listed winners (a display approximation
 *  of the engine's exact odd-chip seat, which is fine here — the engine, not
 *  this UI, is the source of truth for the real payout). */
function computeAwards(log) {
  const awards = {}
  if (!Array.isArray(log)) return awards
  for (let i = log.length - 1; i >= 0; i--) {
    const ev = log[i]
    const type = ev.type ?? ev.kind
    if (type === 'hand_start') break
    if (type === 'pot_award' && Array.isArray(ev.winners) && ev.winners.length && typeof ev.amount === 'number') {
      const share = ev.amount / ev.winners.length
      for (const w of ev.winners) awards[w] = (awards[w] ?? 0) + share
    }
  }
  return awards
}

export function TableScreen({ api, view, storage, onError }) {
  const containerRef = useRef(null)
  const raiseInputRef = useRef(null)
  const now = useNow(1000)
  const reducedMotion = usePrefersReducedMotion()
  const [pending, setPending] = useState(false)
  const [notice, setNotice] = useState(null)
  const [confirmNewTable, setConfirmNewTable] = useState(false)
  const [raiseTo, setRaiseTo] = useState(null)
  const [fourColor, setFourColor] = useState(() => {
    try {
      return Boolean(storage?.get?.(DECK_STORAGE_KEY, false))
    } catch {
      return false
    }
  })

  const selfSeat = view.seats.find(s => s.kind === 'human')?.seat ?? 0
  const laid = useMemo(() => layoutSeats(view.seats, selfSeat), [view.seats, selfSeat])
  const seatsByNo = useMemo(() => Object.fromEntries(view.seats.map(s => [s.seat, s.name])), [view.seats])

  const legal = view.status === 'running' && view.to_act === selfSeat ? view.legal : null

  useEffect(() => {
    if (legal?.min_to != null) setRaiseTo(legal.min_to)
  }, [legal?.seat, legal?.min_to, legal?.max_to])

  function toggleFourColor() {
    setFourColor(v => {
      const next = !v
      try {
        storage?.set?.(DECK_STORAGE_KEY, next)
      } catch {
        // best-effort per-viewer preference only — never load-bearing
      }
      return next
    })
  }

  async function act(kind, to) {
    if (!legal || pending) return
    setPending(true)
    setNotice(null)
    try {
      await api.action({
        turn_id: view.turn_id,
        expected_version: view.version,
        client_action_id: newClientActionId(),
        kind,
        to
      })
    } catch (err) {
      if (err.code === 'stale' || err.code === 'illegal' || err.code === 'not_your_turn' || err.code === 'duplicate') {
        setNotice('The table moved on — refreshing the state.')
      } else {
        setNotice(err.message ?? 'Action failed.')
      }
      onError?.(err)
    } finally {
      setPending(false)
    }
  }

  useBettingShortcuts({
    containerRef,
    legal,
    bb: view.blinds?.bb ?? 10,
    onFold: () => act('fold'),
    onCheckCall: () => act(legal?.can_call ? 'call' : 'check'),
    onFocusRaise: () => raiseInputRef.current?.focus(),
    onAdjust: delta => {
      if (legal?.min_to == null || legal?.max_to == null) return
      setRaiseTo(prev => clamp((prev ?? legal.min_to) + delta, legal.min_to, legal.max_to))
    },
    onSubmit: () => {
      if (legal?.raise_kind && raiseTo != null) act(legal.raise_kind, raiseTo)
    },
    // Spec: "A" stages an all-in TO amount, Enter still confirms it — never
    // submits by itself, so a stray keypress can never shove the stack.
    onAllIn: () => legal?.max_to != null && setRaiseTo(legal.max_to)
  })

  const dealKey = `${view.hand_no}-${view.street}`
  const deadlineSecs = secondsUntil(view.turn_deadline_at, now)
  const nextHandSecs = secondsUntil(view.next_hand_at, now)

  // street is only ever preflop|flop|turn|river|complete in real data
  // (docs/TESTING.md) — "showdown" is checked only as a defensive fallback.
  const handEnded = view.street === 'complete' || view.street === 'showdown'
  const awards = useMemo(() => (handEnded ? computeAwards(view.log) : {}), [handEnded, view.log])
  const winnerSeats = useMemo(() => {
    const fromAwards = Object.keys(awards).map(Number)
    if (fromAwards.length) return new Set(fromAwards)
    return new Set(view.last_hand?.winners ?? [])
  }, [awards, view.last_hand])

  const liveLabel = opponentSummaryLabel(view.seats)
  const isLive = view.status === 'running'
  const statusWord = view.status === 'running' ? 'LIVE' : view.status === 'paused' ? 'PAUSED' : view.status === 'finished' ? 'FINISHED' : view.status.toUpperCase()

  const finishedWinner = view.status === 'finished' ? view.seats.find(s => s.state !== 'out') : null
  const disconnectedNames = view.seats.filter(s => s.agent?.state === 'disconnected').map(s => s.name)
  const attentionText = view.status === 'paused'
    ? 'Table paused — resume when you’re ready.'
    : legal
      ? 'Your turn — choose an action below the table.'
      : disconnectedNames.length
        ? `${disconnectedNames.join(', ')} lost the model connection. The table is using safe fallback moves.`
        : null

  return (
    <div className="ahe-root" ref={containerRef}>
      <div className="ahe-header">
        <div className="ahe-header-left">
          <span className="ahe-live-chip" data-live={String(isLive)}>
            <span className="ahe-live-dot" style={{ animationPlayState: isLive ? 'running' : 'paused' }} /> {statusWord} · {liveLabel}
          </span>
          <span className="ahe-tagline">Bring your agent to the table.</span>
        </div>
        <div className="ahe-header-right">
          <StatusDot tone={view.status === 'running' ? 'good' : view.status === 'paused' ? 'warn' : 'muted'} />
          <span>Hand #{view.hand_no}</span>
          <button type="button" className="ahe-deck-toggle" data-on={String(fourColor)} onClick={toggleFourColor} aria-pressed={fourColor}>
            4-color deck
          </button>
          {view.status === 'running' && (
            <Button size="sm" variant="outline" onClick={() => api.pause().catch(onError)}>
              Pause
            </Button>
          )}
          {view.status === 'paused' && (
            <Button size="sm" onClick={() => api.resume().catch(onError)}>
              Resume
            </Button>
          )}
          <CopyButton text={() => buildHandSummary(view)} label="Copy hand" showLabel buttonVariant="outline" buttonSize="sm" />
          <Button size="sm" variant="ghost" onClick={() => setConfirmNewTable(true)}>
            New table
          </Button>
        </div>
      </div>

      {attentionText && <div className="ahe-attention-banner" role="status"><span aria-hidden="true">✦</span>{attentionText}</div>}

      <div className="ahe-felt-wrap" data-hand-ended={String(handEnded)}>
        <div className="ahe-felt">
          <div className="ahe-felt-inner">
            <BoardArea board={view.board} pots={view.pots} totalPot={view.total_pot} dealKey={dealKey} fourColor={fourColor} />
          </div>
          {laid.map(({ seat, slot }) => {
            const isWinner = handEnded && winnerSeats.has(seat.seat)
            const isLosingReveal = handEnded && Boolean(seat.hole) && !isWinner && seat.seat !== selfSeat
            return (
              <div className="ahe-seat-pos" data-slot={slot} key={seat.seat}>
                <Seat
                  seat={seat}
                  isSelf={seat.seat === selfSeat}
                  isToAct={view.to_act === seat.seat && view.status === 'running'}
                  dealerSeat={view.button}
                  sbSeat={view.sb_seat}
                  bbSeat={view.bb_seat}
                  nowMs={now}
                  dealKey={dealKey}
                  revealed={handEnded}
                  turnStartedAt={view.turn_started_at}
                  turnDeadlineAt={view.turn_deadline_at}
                  reducedMotion={reducedMotion}
                  fourColor={fourColor}
                  isWinner={isWinner}
                  isLosingReveal={isLosingReveal}
                  award={isWinner && awards[seat.seat] != null ? awards[seat.seat] : null}
                />
              </div>
            )
          })}

          {view.status === 'paused' && (
            <div className="ahe-overlay">
              <div className="ahe-overlay-card">
                <div className="ahe-overlay-title">Table paused</div>
                <div className="ahe-overlay-desc">
                  {view.pause_reason === 'restored'
                    ? 'Restored — paused so no tokens are spent until you resume.'
                    : 'No agent will act until you resume.'}
                </div>
                <Button onClick={() => api.resume().catch(onError)}>Resume</Button>
              </div>
            </div>
          )}

          {view.status === 'finished' && (
            <div className="ahe-overlay">
              <div className="ahe-overlay-card">
                <div className="ahe-overlay-title">
                  {finishedWinner ? `${finishedWinner.name} wins the table` : 'Table finished'}
                </div>
                <div className="ahe-overlay-desc">
                  {finishedWinner ? `${fmtChips(finishedWinner.stack)} chips — everyone else busted out.` : 'This table has ended.'}
                </div>
                <Button onClick={() => setConfirmNewTable(true)}>New table</Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {handEnded && view.status === 'running' && (
        <div className="ahe-hand-end" role="status">
          <span className="ahe-hand-end-text">
            {winnerSeats.size > 0
              ? `Hand #${view.last_hand?.hand_no ?? view.hand_no} — ${[...winnerSeats].map(w => seatsByNo[w] ?? `seat ${w}`).join(', ')} won ${fmtChips(
                  view.last_hand?.total_pot ?? view.total_pot
                )}`
              : `Hand #${view.last_hand?.hand_no ?? view.hand_no} ended`}
          </span>
          <span className="ahe-hand-end-sub">
            {nextHandSecs != null ? `Next hand in ${Math.ceil(nextHandSecs)}s` : ''}
          </span>
          <Button size="sm" onClick={() => api.nextHand().catch(onError)}>
            Next hand
          </Button>
        </div>
      )}

      {legal ? (
        <BettingBar
          legal={legal}
          totalPot={view.total_pot}
          bb={view.blinds?.bb ?? 10}
          pending={pending}
          notice={notice}
          raiseInputRef={raiseInputRef}
          raiseTo={raiseTo}
          onRaiseToChange={setRaiseTo}
          onAct={act}
        />
      ) : (
        <div className="ahe-bar" data-disabled="true" aria-live="polite">
          <span role="status">
            {view.status === 'finished'
              ? 'Table finished.'
              : view.status === 'paused'
                ? 'Paused.'
                : view.to_act == null
                  ? handEnded
                    ? 'Hand complete — settling up…'
                    : 'Dealing…'
                  : seatsByNo[view.to_act] != null
                    ? deadlineSecs != null
                      ? `Waiting on ${seatsByNo[view.to_act]} · ${Math.ceil(deadlineSecs)}s left`
                      : `Waiting on ${seatsByNo[view.to_act]}…`
                    : 'Waiting…'}
          </span>
        </div>
      )}

      <div role="status" aria-live="polite" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>
        {view.status === 'running' && view.to_act != null
          ? `${seatsByNo[view.to_act] ?? `Seat ${view.to_act}`} to act`
          : view.status}
      </div>

      <TableChat api={api} view={view} onError={onError} />
      <HistoryPanel log={view.log} seatsByNo={seatsByNo} />

      <ConfirmDialog
        open={confirmNewTable}
        onOpenChange={setConfirmNewTable}
        title="Start a new table?"
        description="This ends the current table and returns everyone to setup. Chip counts reset."
        confirmLabel="New table"
        destructive
        onConfirm={() => api.reset({ confirm: true }).catch(onError)}
      />
    </div>
  )
}
