import { Badge, Button, GlyphSpinner, Kbd } from '@hermes/plugin-sdk'
import { clamp, fmtChips, quickSizes } from '../format.js'

/**
 * Renders ONLY the actions present in `legal`, with exact bounds. Never
 * computes legality itself. `onAct(kind, to?)` is called with the backend's
 * exact vocabulary (fold/check/call/bet/raise/all_in); the caller attaches
 * turn_id/expected_version/client_action_id. The raise amount is lifted to
 * the caller (`raiseTo`/`onRaiseToChange`) so the keyboard shortcuts hook
 * (↑/↓/A/Enter) and this bar always agree on the same number.
 */
export function BettingBar({ legal, totalPot, bb, pending, notice, raiseInputRef, raiseTo, onRaiseToChange, onAct }) {
  if (!legal) return null

  const canRaise = Boolean(legal.raise_kind)
  const raiseWord = legal.raise_kind === 'bet' ? 'Bet' : 'Raise to'
  const sizes = canRaise ? quickSizes(legal, totalPot) : []
  const amount = raiseTo ?? legal.min_to ?? 0

  function setClamped(v) {
    if (legal.min_to == null || legal.max_to == null) return
    onRaiseToChange(clamp(Math.round(v), legal.min_to, legal.max_to))
  }

  function submitRaise() {
    onAct(legal.raise_kind, amount)
  }

  return (
    <div className="ahe-bar" data-disabled={String(pending)} role="group" aria-label="Betting actions">
      <div className="ahe-bar-actions">
        {legal.can_fold && (
          <Button variant="outline" disabled={pending} onClick={() => onAct('fold')}>
            Fold
          </Button>
        )}
        {legal.can_check && (
          <Button disabled={pending} onClick={() => onAct('check')}>
            Check
          </Button>
        )}
        {legal.can_call && (
          <Button disabled={pending} onClick={() => onAct('call')}>
            Call {fmtChips(legal.call_amount)}
          </Button>
        )}
        {pending && (
          <span className="ahe-bar-pending" role="status">
            <GlyphSpinner ariaLabel="Sending" /> Sending…
          </span>
        )}
      </div>

      {canRaise && (
        <div className="ahe-bar-raise">
          <input
            ref={raiseInputRef}
            className="ahe-bar-amount"
            type="number"
            min={legal.min_to}
            max={legal.max_to}
            step={bb}
            value={amount}
            disabled={pending}
            aria-label={`${raiseWord} amount`}
            onChange={e => setClamped(Number(e.target.value))}
          />
          <input
            className="ahe-bar-slider"
            type="range"
            min={legal.min_to}
            max={legal.max_to}
            step={1}
            value={amount}
            disabled={pending}
            aria-label={`${raiseWord} slider`}
            onChange={e => setClamped(Number(e.target.value))}
          />
          <div className="ahe-bar-quicksizes">
            {sizes.map(s => (
              <Button key={s.label} size="sm" variant="ghost" disabled={pending} onClick={() => setClamped(s.to)}>
                {s.label}
              </Button>
            ))}
          </div>
          <Button disabled={pending} onClick={submitRaise}>
            {raiseWord} {fmtChips(amount)}
          </Button>
        </div>
      )}

      <div className="ahe-bar-meta">
        To call {fmtChips(legal.to_call)} · Stack {fmtChips(legal.stack)}
      </div>

      {notice && (
        <Badge variant="destructive" className="ahe-bar-notice">
          {notice}
        </Badge>
      )}

      <div className="ahe-kbd-hint" aria-hidden="true">
        <span>
          <Kbd>F</Kbd> Fold
        </span>
        <span>
          <Kbd>C</Kbd> Check/Call
        </span>
        <span>
          <Kbd>R</Kbd> Raise
        </span>
        <span>
          <Kbd>↑↓</Kbd> ±BB
        </span>
        <span>
          <Kbd>A</Kbd> All-in
        </span>
        <span>
          <Kbd>Enter</Kbd> Confirm
        </span>
      </div>
    </div>
  )
}
