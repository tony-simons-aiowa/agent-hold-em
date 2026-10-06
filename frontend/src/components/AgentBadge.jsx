import { GlyphSpinner, Tip } from '@hermes/plugin-sdk'
import { fallbackReason, fmtChips, fmtCompact, fmtPct, styleLabel } from '../format.js'

/**
 * Status tags for a seat: thinking (with elapsed seconds), folded, all-in,
 * out, fallback, disconnected/error. Renders zero or more small pills.
 */
export function AgentBadgeRow({ seat, nowMs }) {
  const tags = []
  const agent = seat.agent
  const state = seat.state

  if (agent?.state === 'thinking') {
    const elapsed = agent.since != null ? Math.max(0, Math.round(nowMs / 1000 - agent.since)) : null
    tags.push(
      <span className="ahe-tag" data-kind="thinking" key="thinking">
        <GlyphSpinner ariaLabel="Thinking" />
        Thinking{elapsed != null ? ` · ${elapsed}s` : ''}
      </span>
    )
  } else if (agent?.state === 'error') {
    tags.push(
      <span className="ahe-tag" data-kind="error" key="error">
        Error{agent.last_error ? `: ${agent.last_error}` : ''}
      </span>
    )
  } else if (agent?.state === 'disconnected') {
    tags.push(
      <span className="ahe-tag" data-kind="disconnected" key="disconnected">
        Disconnected
      </span>
    )
  }

  if (seat.last_action?.fallback) {
    const verb = seat.last_action.kind === 'check' ? 'Auto-checked' : 'Auto-folded'
    tags.push(
      <span className="ahe-tag" data-kind="fallback" key="fallback">
        {verb} — {fallbackReason(seat)}
      </span>
    )
  }

  if (state === 'folded') {
    tags.push(
      <span className="ahe-tag" data-kind="folded" key="folded">
        Folded
      </span>
    )
  }
  if (state === 'all_in') {
    tags.push(
      <span className="ahe-tag" data-kind="allin" key="allin">
        All-in
      </span>
    )
  }
  if (state === 'out') {
    tags.push(
      <span className="ahe-tag" data-kind="folded" key="out">
        Out
      </span>
    )
  }
  if (seat.kind === 'test_bot') {
    tags.push(
      <span className="ahe-tag" data-kind="testbot" key="testbot">
        <span className="ahe-testbot-long">TEST BOT — not an agent</span>
        <span className="ahe-testbot-short">TEST BOT</span>
      </span>
    )
  }

  if (tags.length === 0) return <div className="ahe-badge-row" />
  return <div className="ahe-badge-row">{tags}</div>
}

/** Persona chip: avatar + name + personality + model, with a stats tooltip. */
export function StatsTooltipContent({ seat }) {
  const stats = seat.stats
  const label = styleLabel(stats)
  return (
    <div>
      <div>
        <strong>{seat.model_label ?? 'Unknown model'}</strong>
      </div>
      {seat.personality ? <div>Personality: {seat.personality}</div> : null}
      {label ? <div>Style: {label}</div> : null}
      {stats ? (
        <div>
          Hands {stats.hands} · VPIP {fmtPct(stats.vpip)} · PFR {fmtPct(stats.pfr)} · AF {stats.af?.toFixed?.(1) ?? '—'}
        </div>
      ) : (
        <div>No hands played yet</div>
      )}
      {agentTokens(seat)}
    </div>
  )
}

function agentTokens(seat) {
  const tokens = seat.agent?.tokens
  if (!tokens) return null
  return <div>Tokens: {fmtChips(tokens.total)} total (this table)</div>
}

export function StyleChip({ seat }) {
  const label = styleLabel(seat.stats)
  if (!label) return null
  return (
    <Tip label={<StatsTooltipContent seat={seat} />}>
      <span className="ahe-tag" data-kind="folded" style={{ cursor: 'default' }}>
        {label}
      </span>
    </Tip>
  )
}

/** Small token-usage indicator for a Hermes seat — a tooltip explains what it
 *  means (this is inference cost, not a game stat) so it never reads as a
 *  mystery number. Only rendered for real agent seats. */
export function TokenChip({ seat }) {
  const tokens = seat.agent?.tokens
  if (seat.kind !== 'hermes' || !tokens) return null
  return (
    <Tip label={`This Hermes agent's token usage for this table: ${fmtChips(tokens.input)} in / ${fmtChips(tokens.output)} out`}>
      <span className="ahe-token-chip">
        <span aria-hidden="true">◆</span> {fmtCompact(tokens.total)} tok
      </span>
    </Tip>
  )
}
