import { useEffect, useRef, useState } from 'react'
import { host, useQuery, useQueryClient } from '@hermes/plugin-sdk'

export const STATE_QUERY_KEY = ['agent-hold-em', 'state']
const REFETCH_MS = 2500 // spec: keep >= 2s even while an agent is "thinking"

/**
 * Poll GET /state via the app's React Query client, invalidated early by the
 * plugin.<id>.table.changed push event. Falls back to polling alone when no
 * event ever arrives (OAuth remotes / socket-less installs).
 */
export function useTableState(api) {
  const client = useQueryClient()
  const query = useQuery({
    queryKey: STATE_QUERY_KEY,
    queryFn: () => api.state(),
    refetchInterval: query => query.state.status === 'error' ? 15_000 : REFETCH_MS,
    retry: false
  })

  useEffect(() => {
    return host.onEvent('plugin.agent-hold-em.table.changed', () => {
      client.invalidateQueries({ queryKey: STATE_QUERY_KEY })
    })
  }, [client])

  return query
}

/** A ticking clock (1x/second) for deadline rings and "thinking Ns" labels.
 *  A single shared interval per mounted consumer; cleared on unmount. */
export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false
  )
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])
  return reduced
}

/**
 * Keyboard shortcuts for the betting bar: F fold, C check/call, R focus raise
 * input, Enter submit, ArrowUp/Down +-BB, A all-in (needs Enter to confirm).
 * Only active while the page/pane has focus and the user isn't typing in an
 * unrelated field. All state is read via refs so handlers never see stale
 * closures from a render that already passed.
 */
export function useBettingShortcuts({ containerRef, legal, bb, onFold, onCheckCall, onFocusRaise, onAdjust, onSubmit, onAllIn }) {
  const stateRef = useRef({ legal, bb, onFold, onCheckCall, onFocusRaise, onAdjust, onSubmit, onAllIn })
  stateRef.current = { legal, bb, onFold, onCheckCall, onFocusRaise, onAdjust, onSubmit, onAllIn }

  useEffect(() => {
    function isTypingTarget(el) {
      if (!el) return false
      const tag = el.tagName
      return tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable
    }

    function onKeyDown(e) {
      const s = stateRef.current
      if (!s.legal) return
      const root = containerRef.current
      if (!root) return
      // Only act while focus is within this page's container.
      if (!root.contains(document.activeElement) && document.activeElement !== document.body) return
      if (isTypingTarget(document.activeElement) && e.key !== 'Enter' && e.key !== 'Escape') return

      switch (e.key) {
        case 'f':
        case 'F':
          if (s.legal.can_fold) {
            e.preventDefault()
            s.onFold()
          }
          break
        case 'c':
        case 'C':
          if (s.legal.can_check || s.legal.can_call) {
            e.preventDefault()
            s.onCheckCall()
          }
          break
        case 'r':
        case 'R':
          if (s.legal.raise_kind) {
            e.preventDefault()
            s.onFocusRaise()
          }
          break
        case 'ArrowUp':
          if (s.legal.raise_kind) {
            e.preventDefault()
            s.onAdjust(s.bb)
          }
          break
        case 'ArrowDown':
          if (s.legal.raise_kind) {
            e.preventDefault()
            s.onAdjust(-s.bb)
          }
          break
        case 'a':
        case 'A':
          if (s.legal.raise_kind) {
            e.preventDefault()
            s.onAllIn()
          }
          break
        case 'Enter':
          if (isTypingTarget(document.activeElement)) {
            e.preventDefault()
            s.onSubmit()
          }
          break
        default:
          break
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [containerRef])
}
