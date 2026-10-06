import { CardRow } from './Card.jsx'
import { AgentBadgeRow, StyleChip, TokenChip } from './AgentBadge.jsx'
import { TalkBubble } from './TalkBubble.jsx'
import { ProfileAvatar } from './ProfileAvatar.jsx'
import { fmtChips, ringFraction, secondsUntil } from '../format.js'

const RING_R = 17
const RING_C = 2 * Math.PI * RING_R

/** Countdown ring around an agent's avatar, driven by the table's own
 *  turn_started_at/turn_deadline_at (NOT any per-seat field — those aren't
 *  in HumanView). Falls back to a plain "Ns" text under reduced motion. */
function DeadlineRing({ startedAt, deadlineAt, nowMs, reducedMotion }) {
  const frac = ringFraction(startedAt, deadlineAt, nowMs)
  if (frac == null) return null

  if (reducedMotion) {
    const left = Math.ceil(secondsUntil(deadlineAt, nowMs) ?? 0)
    return (
      <span className="ahe-deadline-ring" aria-hidden="true" style={{ display: 'grid', placeItems: 'center', color: 'var(--ui-text-secondary)', fontSize: '0.6rem', fontWeight: 700 }}>
        {left}s
      </span>
    )
  }

  const dash = RING_C * frac
  return (
    <svg className="ahe-deadline-ring" width="36" height="36" viewBox="0 0 36 36" aria-hidden="true">
      <circle cx="18" cy="18" r={RING_R} fill="none" stroke="var(--ui-stroke-secondary)" strokeWidth="2" />
      <circle
        cx="18"
        cy="18"
        r={RING_R}
        fill="none"
        stroke={frac < 0.25 ? 'var(--ui-danger)' : 'var(--ahe-glow)'}
        strokeWidth="2"
        strokeDasharray={`${dash} ${RING_C}`}
        strokeLinecap="round"
      />
    </svg>
  )
}

/**
 * One seat: avatar + name/model, hole cards (own or hidden), stack, committed
 * chips, dealer/blind markers, status badges, and chatter. Renders exactly
 * what HumanView gives — no legality or payout computation happens here.
 */
export function Seat({
  seat,
  isSelf,
  isToAct,
  dealerSeat,
  sbSeat,
  bbSeat,
  nowMs,
  dealKey,
  revealed,
  turnStartedAt,
  turnDeadlineAt,
  reducedMotion,
  fourColor,
  isWinner,
  isLosingReveal,
  award
}) {
  const showThinkingRing = seat.agent?.state === 'thinking' && isToAct
  const showHole = isSelf || (revealed && seat.hole)

  return (
    <div
      className="ahe-seat"
      data-active={String(isToAct)}
      data-state={seat.state}
      data-winner={String(Boolean(isWinner))}
      data-dimmed={String(Boolean(isLosingReveal))}
    >
      <TalkBubble talk={seat.talk} />
      {award != null && (
        <div className="ahe-seat-award" role="status">
          +{fmtChips(award)}
        </div>
      )}
      <div className="ahe-seat-markers">
        {seat.seat === dealerSeat && (
          <span className="ahe-seat-marker" data-kind="d">
            D
          </span>
        )}
        {seat.seat === sbSeat && (
          <span className="ahe-seat-marker" data-kind="sb">
            SB
          </span>
        )}
        {seat.seat === bbSeat && (
          <span className="ahe-seat-marker" data-kind="bb">
            BB
          </span>
        )}
      </div>

      <div className="ahe-seat-top">
        <div className="ahe-avatar" aria-hidden="true">
          {showThinkingRing && (
            <DeadlineRing startedAt={turnStartedAt} deadlineAt={turnDeadlineAt} nowMs={nowMs} reducedMotion={reducedMotion} />
          )}
          <ProfileAvatar avatar={seat.avatar ?? (seat.kind === 'human' ? '🧑' : '🤖')} size={30} />
        </div>
        <div className="ahe-seat-name-wrap">
          <div className="ahe-seat-name">{seat.name}</div>
          <div className="ahe-seat-sub">
            {seat.kind === 'human'
              ? 'You'
              : [seat.personality, seat.model_label].filter(Boolean).join(' · ') || (seat.kind === 'test_bot' ? 'Scripted' : 'Agent')}
          </div>
        </div>
      </div>

      <CardRow
        cards={showHole ? seat.hole : undefined}
        count={2}
        faceDown={!showHole}
        size={isSelf ? 'lg' : 'sm'}
        dealKey={dealKey}
        fourColor={fourColor}
        dim={isLosingReveal}
      />

      <div className="ahe-seat-stack">{fmtChips(seat.stack)} chips</div>

      <AgentBadgeRow seat={seat} nowMs={nowMs} />
      <div className="ahe-seat-chips-row">
        <StyleChip seat={seat} />
        <TokenChip seat={seat} />
      </div>

      {seat.hand_label && revealed ? (
        <div className="ahe-tag" data-kind={isWinner ? 'winner' : 'folded'}>
          {seat.hand_label}
        </div>
      ) : null}

      {seat.committed > 0 && (
        <div className="ahe-seat-committed" key={`${seat.seat}-${seat.committed}`}>
          <span aria-hidden="true">●</span> {fmtChips(seat.committed)}
        </div>
      )}
    </div>
  )
}
