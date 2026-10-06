import { parseCard } from '../format.js'

// The card face background stays a light cream in both themes (see
// styles.js --ahe-card-bg), so one fixed palette reads clearly everywhere.
const FOUR_COLOR = { s: '#1a1a1a', c: '#1c7a3c', d: '#1c5fc7', h: '#c62828' }

/**
 * One playing card, or a face-down back. `size` is 'lg' (the human's own hole
 * cards), 'md' (board, default) or 'sm' (opponent hole cards / compact
 * contexts). Purely presentational — never used to infer legality.
 * `winning`/`dim` are showdown-only highlight hints (also presentational).
 */
export function Card({ card, faceDown, size = 'md', anim, fourColor, winning, dim }) {
  const sizeClass = size === 'sm' ? ' ahe-card-sm' : size === 'lg' ? ' ahe-card-lg' : ''

  if (faceDown || !card) {
    return <div className={`ahe-card ahe-card-back${sizeClass}`} data-anim={anim} aria-hidden="true" />
  }

  const parsed = parseCard(card)
  if (!parsed) return null

  const style = fourColor && FOUR_COLOR[parsed.suit] ? { color: FOUR_COLOR[parsed.suit] } : undefined

  return (
    <div
      className={`ahe-card${sizeClass}`}
      data-red={String(parsed.red)}
      data-suit={parsed.suit}
      data-anim={anim}
      data-winning={winning ? 'true' : undefined}
      data-dim={dim ? 'true' : undefined}
      style={style}
      role="img"
      aria-label={`${parsed.rank} of ${parsed.name}`}
    >
      <span className="ahe-card-corner">
        <span>{parsed.rank}</span>
        <span>{parsed.glyph}</span>
      </span>
      <span className="ahe-card-rank">{parsed.rank}</span>
      <span className="ahe-card-suit">{parsed.glyph}</span>
    </div>
  )
}
/** A row of cards (board, or a seat's hole cards). */
export function CardRow({ cards, count, faceDown, size, dealKey, fourColor, winning, dim }) {
  const n = count ?? cards?.length ?? 0
  const slots = Array.from({ length: n }, (_, i) => i)
  return (
    <div className="ahe-card-slot">
      {slots.map(i => (
        <Card
          key={dealKey ? `${dealKey}-${i}` : i}
          card={cards?.[i]}
          faceDown={faceDown || !cards?.[i]}
          size={size}
          fourColor={fourColor}
          winning={winning}
          dim={dim}
          anim={dealKey ? 'deal' : undefined}
        />
      ))}
    </div>
  )
}
