import { useState } from 'react'
import { Codicon, ScrollArea } from '@hermes/plugin-sdk'
import { fmtChips } from '../format.js'

function describeEvent(ev) {
  switch (ev.type ?? ev.kind) {
    case 'hand_start':
      return `Hand #${ev.hand_no} — new deal`
    case 'blinds':
      return `Blinds posted`
    case 'street':
      return `${ev.name?.toUpperCase?.() ?? 'Street'}${ev.board ? ` — ${ev.board.join(' ')}` : ''}`
    case 'action':
      return `${ev.kind}${ev.to != null ? ` to ${fmtChips(ev.to)}` : ''}`
    case 'uncalled_return':
      return `Uncalled ${fmtChips(ev.amount)} returned`
    case 'showdown':
      return 'Showdown'
    case 'pot_award':
      return `Pot ${fmtChips(ev.amount)} awarded${ev.split ? ' (split)' : ''}`
    case 'bust':
      return 'Busted out'
    case 'hand_end':
      return 'Hand ended'
    case 'table_over':
      return 'Table over'
    default:
      return ev.type ?? ev.kind ?? 'Event'
  }
}

/** Collapsible, keyboard-reachable public hand-history log. Public data only. */
export function HistoryPanel({ log, seatsByNo }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="ahe-history">
      <div
        className="ahe-history-head"
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setOpen(o => !o)
          }
        }}
      >
        <span className="ahe-history-title">Hand history</span>
        <Codicon name={open ? 'chevron-up' : 'chevron-down'} />
      </div>
      {open && (
        <ScrollArea className="ahe-history-body">
          {(!log || log.length === 0) && <div className="ahe-log-row">No events yet.</div>}
          {log?.map((ev, i) => (
            <div className="ahe-log-row" key={i}>
              {ev.seat != null && seatsByNo?.[ev.seat] && <span className="ahe-log-seat">{seatsByNo[ev.seat]}</span>}
              <span>{describeEvent(ev)}</span>
            </div>
          ))}
        </ScrollArea>
      )}
    </div>
  )
}
