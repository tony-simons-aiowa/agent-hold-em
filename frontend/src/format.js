// Small pure helpers shared by the UI. No game logic lives here — everything
// here is presentation-only formatting of what the backend already decided.

const SUIT_GLYPH = { s: '♠', h: '♥', d: '♦', c: '♣' }
const SUIT_NAME = { s: 'spades', h: 'hearts', d: 'diamonds', c: 'clubs' }
const RANK_LABEL = { T: '10' }

/** Parse a two-character card string like "Ah", "Td", "9c" into parts. */
export function parseCard(card) {
  if (!card || card.length < 2) return null
  const rank = card[0].toUpperCase()
  const suit = card[1].toLowerCase()
  return {
    rank: RANK_LABEL[rank] ?? rank,
    suit,
    glyph: SUIT_GLYPH[suit] ?? '?',
    name: SUIT_NAME[suit] ?? 'unknown',
    red: suit === 'h' || suit === 'd'
  }
}

export function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

/** Format a chip count compactly (1200 -> "1,200"). Chips are not currency. */
export function fmtChips(n) {
  if (n == null || Number.isNaN(n)) return '—'
  return Math.round(n).toLocaleString('en-US')
}

export function fmtPct(n) {
  if (n == null || Number.isNaN(n)) return '—'
  return `${Math.round(n * 100)}%`
}

export function fmtSeconds(s) {
  const v = Math.max(0, Math.round(s))
  return `${v}s`
}

/** Compact "4.6k" style formatting for token counts. */
export function fmtCompact(n) {
  if (n == null || Number.isNaN(n)) return '—'
  if (n < 1000) return String(Math.round(n))
  return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`
}

/** Seconds remaining until an epoch-seconds deadline, clamped to >= 0. */
export function secondsUntil(epochSeconds, nowMs = Date.now()) {
  if (epochSeconds == null) return null
  return Math.max(0, epochSeconds - nowMs / 1000)
}

/** 0..1 fraction of a countdown ring remaining. */
export function ringFraction(startedAt, deadlineAt, nowMs = Date.now()) {
  if (startedAt == null || deadlineAt == null) return null
  const total = deadlineAt - startedAt
  if (total <= 0) return 0
  const remaining = deadlineAt - nowMs / 1000
  return clamp(remaining / total, 0, 1)
}

/** Derive a short playstyle label from public stats — cosmetic only, never
 *  used for anything the engine decides. Requires >= 8 hands so an early
 *  read never masquerades as a settled one; before that we say so. */
export function styleLabel(stats) {
  if (!stats || stats.hands == null) return null
  if (stats.hands < 8) return 'Reading…'
  const { vpip, pfr } = stats
  if (vpip == null || pfr == null) return 'Reading…'
  if (vpip >= 0.45 && pfr >= 0.3) return 'Loose-aggressive'
  if (vpip >= 0.45 && pfr < 0.3) return 'Loose-passive'
  if (vpip < 0.3 && pfr >= 0.2) return 'Tight-aggressive'
  if (vpip < 0.3 && pfr < 0.15) return 'Tight-passive'
  return 'Balanced'
}

/** Quick raise-size presets in TO terms, clamped to [min_to, max_to], with
 *  duplicates (once clamped) collapsed so e.g. Min and Pot never render as
 *  two buttons for the same amount. */
export function quickSizes(legal, totalPot) {
  if (!legal) return []
  const { min_to, max_to } = legal
  if (min_to == null || max_to == null) return []
  const sizes = [
    { label: 'Min', to: min_to },
    { label: '½ Pot', to: Math.round(totalPot * 0.5) },
    { label: '¾ Pot', to: Math.round(totalPot * 0.75) },
    { label: 'Pot', to: totalPot },
    { label: 'All-in', to: max_to }
  ]
  const seen = new Set()
  return sizes
    .map(s => ({ ...s, to: clamp(s.to, min_to, max_to) }))
    .filter(s => {
      if (seen.has(s.to)) return false
      seen.add(s.to)
      return true
    })
}

/**
 * Honest composition label for the header chip — never claims "Hermes
 * agents" for a seat that isn't one. Counts opponent seats (kind != human)
 * by kind and renders e.g. "3 Hermes agents" or "2 Hermes agents + 1 test bot".
 */
export function opponentSummaryLabel(seats) {
  const opponents = (seats ?? []).filter(s => s.kind !== 'human')
  const agents = opponents.filter(s => s.kind === 'hermes').length
  const bots = opponents.filter(s => s.kind === 'test_bot').length
  const parts = []
  if (agents > 0) parts.push(`${agents} Hermes agent${agents === 1 ? '' : 's'}`)
  if (bots > 0) parts.push(`${bots} test bot${bots === 1 ? '' : 's'}`)
  return parts.join(' + ') || 'No opponents'
}

/** Human-readable reason for a forced fallback action, best-effort from the
 *  fields HumanView actually exposes (Action.fallback is just a bool — the
 *  reason is inferred from the agent's own reported error, never invented
 *  beyond "timeout" vs "invalid reply"). */
export function fallbackReason(seat) {
  if (seat.agent?.last_error) return 'invalid reply'
  return 'timeout'
}
