/**
 * Short speech bubble above a seat, keyed by the talk text itself so a NEW
 * line replays the fade-in/out animation (see styles.js: ahe-bubble-out
 * delays 3.6s then fades over 400ms — ~4s total display).
 */
export function TalkBubble({ talk }) {
  if (!talk) return null
  return (
    <div className="ahe-bubble" key={talk} role="status">
      {talk}
    </div>
  )
}
