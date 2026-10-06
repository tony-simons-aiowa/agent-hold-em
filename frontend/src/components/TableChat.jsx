import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@hermes/plugin-sdk'
import { ProfileAvatar } from './ProfileAvatar.jsx'
import { STATE_QUERY_KEY } from '../hooks.js'

export function TableChat({ api, view, onError }) {
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const feedRef = useRef(null)
  const queryClient = useQueryClient()
  const messages = view.chat ?? []
  const lastId = messages.at(-1)?.id
  const seats = Object.fromEntries(view.seats.map(seat => [seat.seat, seat]))

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight
  }, [lastId])

  async function send(event) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || sending) return
    setSending(true)
    setError('')
    try {
      const nextView = await api.chat({ text })
      // Chat does not bump the service version (it is not game state), so an equal-version
      // response can still carry a newer chat log. Accept it only when it is strictly newer
      // in version (a real mutation won the race) or equal in version with more chat.
      queryClient.setQueryData(STATE_QUERY_KEY, current => {
        if (!current) return nextView
        if (nextView.version > current.version) return nextView
        if (nextView.version === current.version && (nextView.chat?.length ?? 0) > (current.chat?.length ?? 0)) return nextView
        return current
      })
      setDraft('')
    } catch (err) {
      setError(err.message ?? 'Could not send your message.')
      onError?.(err)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="ahe-chat" aria-label="Table chat">
      <div className="ahe-chat-head">
        <div>
          <strong>Table chat</strong>
          <span>Agents speak as they play · replies come on their turns</span>
        </div>
        <span className="ahe-chat-count">{messages.length} messages</span>
      </div>
      <div className="ahe-chat-feed" ref={feedRef} role="log" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 && <p className="ahe-chat-empty">The table is quiet. Say something to get it started.</p>}
        {messages.map(msg => {
          const seat = seats[msg.seat]
          return (
            <div className="ahe-chat-line" data-kind={msg.kind} data-level={msg.level ?? 'info'} key={msg.id}>
              <span className="ahe-chat-avatar" aria-hidden="true">
                {msg.kind === 'system' ? '✦' : <ProfileAvatar avatar={seat?.avatar} size={24} />}
              </span>
              <div className="ahe-chat-copy">
                <span className="ahe-chat-name">{msg.kind === 'system' ? 'Table' : seat?.name ?? (msg.kind === 'human' ? 'You' : 'Agent')}</span>
                <span className="ahe-chat-text">{msg.text}</span>
              </div>
            </div>
          )
        })}
      </div>
      <form className="ahe-chat-compose" onSubmit={send}>
        <input
          type="text"
          value={draft}
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => event.stopPropagation()}
          maxLength={160}
          disabled={view.status === 'finished' || sending}
          aria-label="Message the table"
          placeholder="Talk to the table…"
        />
        <button type="submit" disabled={!draft.trim() || sending || view.status === 'finished'}>Send</button>
      </form>
      {error && <div className="ahe-chat-error" role="alert">{error}</div>}
    </section>
  )
}
