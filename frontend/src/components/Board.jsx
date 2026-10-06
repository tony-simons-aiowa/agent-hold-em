import { CardRow } from './Card.jsx'
import { fmtChips } from '../format.js'

/** Community board + pot(s)/side-pots. Renders exactly what HumanView gives. */
export function BoardArea({ board, pots, totalPot, dealKey, fourColor }) {
  return (
    <div className="ahe-board-area">
      <div className="ahe-board-cards">
        <CardRow cards={board} count={Math.max(board?.length ?? 0, 0)} dealKey={dealKey} fourColor={fourColor} />
      </div>
      <div className="ahe-pot-row">
        <span className="ahe-pot-chip">Pot {fmtChips(totalPot)}</span>
        {pots && pots.length > 1
          ? pots.map((p, i) => (
              <span className="ahe-pot-chip" key={i}>
                Side {i + 1}: {fmtChips(p.amount)} <small>({p.eligible.length} eligible)</small>
              </span>
            ))
          : null}
      </div>
    </div>
  )
}
