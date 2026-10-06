// Scoped CSS for Agent Hold 'Em. Injected once via ensureStyles(), using the
// content-compare idempotent pattern (see the hermes-desktop-plugins skill's
// "stale scoped CSS on hot-reload" pitfall — a static id check alone would
// freeze the FIRST version of this file across every later hot-reload save).
// Every selector is prefixed `.ahe-`. Chrome uses the app's --ui-* theme
// variables; the felt/card faces define their own scoped custom properties
// under `.ahe-root`, overridden for dark mode via the app's `.dark` class on
// <html> (apps/desktop/src/themes/context.tsx sets `classList.toggle('dark', isDark)`).

const STYLE_ID = 'agent-hold-em-styles'

const CSS = `
.ahe-root {
  --ahe-felt-1: #0f3d2e;
  --ahe-felt-2: #145c41;
  --ahe-felt-edge: #06231a;
  --ahe-rail: #3a2213;
  --ahe-rail-light: #5c3a1f;
  --ahe-card-bg: #fbfaf6;
  --ahe-card-border: rgba(0,0,0,0.14);
  --ahe-card-red: #c62828;
  --ahe-card-black: #1a1a1a;
  --ahe-card-back-1: #7a1f2b;
  --ahe-card-back-2: #4a1019;
  --ahe-gold: #d8b25c;
  --ahe-glow: #ffd873;
  --ahe-win: #6fce7f;
  --ahe-chip-1: #d94a4a;
  --ahe-chip-2: #4a7fd9;
  --ahe-chip-3: #4ad97e;
  --ahe-chip-4: #2b2b2b;
  --ahe-seat-bg: color-mix(in srgb, var(--ui-bg-elevated, #222) 88%, black);
  --ahe-shadow: rgba(0,0,0,0.45);
  color-scheme: light;
}
.dark .ahe-root {
  --ahe-felt-1: #0b2e22;
  --ahe-felt-2: #0f4531;
  --ahe-felt-edge: #041a13;
  --ahe-rail: #2a1a10;
  --ahe-rail-light: #46301c;
  --ahe-card-bg: #f5f3ec;
  --ahe-card-border: rgba(0,0,0,0.2);
  --ahe-card-red: #e05353;
  --ahe-card-black: #16171a;
  --ahe-seat-bg: color-mix(in srgb, var(--ui-bg-elevated, #111) 92%, black);
  --ahe-shadow: rgba(0,0,0,0.65);
  color-scheme: dark;
}

.ahe-root {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  padding: 0.85rem clamp(0.6rem, 2vw, 1.25rem) 1rem;
  box-sizing: border-box;
  color: var(--ui-text-primary);
  font-variant-numeric: tabular-nums;
  container-type: inline-size;
  container-name: ahe;
  overflow-y: auto;
}
.ahe-root *, .ahe-root *::before, .ahe-root *::after { box-sizing: border-box; }
.ahe-root :focus-visible { outline: 2px solid var(--ui-accent); outline-offset: 2px; }

/* ---------- header ---------- */
.ahe-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.ahe-header-left { display: flex; align-items: center; gap: 0.6rem; min-width: 0; flex-wrap: wrap; }
.ahe-live-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: var(--ui-danger, #e05353);
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--ui-danger, #e05353) 45%, transparent);
  background: color-mix(in srgb, var(--ui-danger, #e05353) 12%, transparent);
  white-space: nowrap;
}
.ahe-live-chip[data-live="false"] {
  color: var(--ui-text-tertiary);
  border-color: var(--ui-stroke-secondary);
  background: var(--ui-bg-secondary);
}
.ahe-live-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor;
  animation: ahe-pulse 1.6s ease-in-out infinite;
}
.ahe-tagline { font-size: 0.78rem; color: var(--ui-text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ahe-title { font-size: 1rem; font-weight: 650; margin: 0; white-space: nowrap; }
.ahe-header-right { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.ahe-deck-toggle {
  font-size: 0.68rem; font-weight: 600; color: var(--ui-text-tertiary);
  border: 1px solid var(--ui-stroke-secondary); background: transparent;
  border-radius: 999px; padding: 0.15rem 0.55rem; cursor: pointer;
}
.ahe-deck-toggle[data-on="true"] { color: var(--ui-accent); border-color: var(--ui-accent); background: color-mix(in srgb, var(--ui-accent) 12%, transparent); }

/* ---------- felt ---------- */
.ahe-felt-wrap {
  position: relative;
  flex: 1 1 auto;
  min-height: 600px;
  border-radius: clamp(18px, 4vw, 34px);
  padding: clamp(10px, 2.2vw, 22px);
  background: linear-gradient(180deg, var(--ahe-rail-light), var(--ahe-rail));
  box-shadow: 0 10px 30px var(--ahe-shadow), inset 0 0 0 2px rgba(255,255,255,0.04);
}
.ahe-felt-wrap[data-hand-ended="true"] { min-height: 680px; }
.ahe-felt {
  position: relative;
  height: 100%;
  width: 100%;
  border-radius: clamp(14px, 3.4vw, 28px);
  background:
    radial-gradient(ellipse at 50% 38%, var(--ahe-felt-2) 0%, var(--ahe-felt-1) 62%, var(--ahe-felt-edge) 100%);
  box-shadow: inset 0 0 0 3px rgba(0,0,0,0.25), inset 0 20px 60px rgba(0,0,0,0.35);
  overflow: hidden;
}
.ahe-felt::before {
  /* subtle vignette — purely decorative, sits under everything else */
  content: '';
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(0,0,0,0.28) 100%);
  pointer-events: none;
  z-index: 0;
}
.ahe-felt-inner {
  position: absolute; inset: 0;
  display: grid;
  place-items: center;
}

/* seat grid — percentage-anchored positions around an oval, human bottom-center */
.ahe-seat-pos {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  width: clamp(96px, 22cqw, 168px);
  transition: filter 200ms ease;
  z-index: 1;
}
.ahe-seat-pos[data-slot="human"]   { left: 50%; bottom: 5%;  transform: translate(-50%, 0); width: clamp(104px, 23cqw, 172px); }
.ahe-seat-pos[data-slot="left"]    { left: 4%;  top: 50%;    transform: translate(0, -50%); }
.ahe-seat-pos[data-slot="top"]     { left: 50%; top: 5%;     transform: translate(-50%, 0); }
.ahe-seat-pos[data-slot="right"]   { right: 4%; top: 50%;    transform: translate(0, -50%); }

/* ---------- board / pot ---------- */
.ahe-board-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  z-index: 1;
}
.ahe-board-cards { display: flex; gap: clamp(4px, 1cqw, 8px); min-height: 1px; }
.ahe-pot-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; justify-content: center; max-width: 38cqw; margin: 0 auto; }
.ahe-pot-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.78rem;
  font-weight: 650;
  color: var(--ahe-glow);
  background: rgba(0,0,0,0.35);
  border: 1px solid rgba(255,255,255,0.12);
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
}
.ahe-pot-chip small { font-weight: 500; opacity: 0.75; }

/* ---------- cards ---------- */
.ahe-card {
  position: relative;
  width: clamp(38px, 7.6cqw, 64px);
  aspect-ratio: 5 / 7;
  border-radius: clamp(4px, 0.8cqw, 7px);
  background: var(--ahe-card-bg);
  border: 1px solid var(--ahe-card-border);
  box-shadow: 0 2px 6px rgba(0,0,0,0.35);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  line-height: 1;
  user-select: none;
  transform-style: preserve-3d;
}
.ahe-card[data-anim="deal"] { animation: ahe-deal 260ms cubic-bezier(.2,.8,.3,1) both; }
.ahe-card-rank { font-weight: 750; font-size: clamp(0.85rem, 2.6cqw, 1.4rem); }
.ahe-card-suit { font-size: clamp(0.9rem, 2.8cqw, 1.55rem); margin-top: -0.1em; }
.ahe-card[data-red="true"] { color: var(--ahe-card-red); }
.ahe-card[data-red="false"] { color: var(--ahe-card-black); }
.ahe-card[data-suit="s"], .ahe-card[data-suit="c"] { color: var(--ahe-card-black); }
.ahe-card-corner {
  position: absolute; top: 3%; left: 8%;
  font-size: clamp(0.5rem, 1.4cqw, 0.7rem);
  font-weight: 700;
  display: flex; flex-direction: column; align-items: center; line-height: 1.05;
}
.ahe-card.ahe-card-sm { width: clamp(26px, 5.4cqw, 42px); }
.ahe-card.ahe-card-lg { width: clamp(44px, 8.4cqw, 70px); box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
.ahe-card[data-winning="true"] {
  box-shadow: 0 0 0 2px var(--ahe-win), 0 0 16px color-mix(in srgb, var(--ahe-win) 60%, transparent);
}
.ahe-card[data-dim="true"] { opacity: 0.45; filter: grayscale(0.35); }
/* Original geometric card back — a diamond lattice tinted with the app's own
   accent color (no logos/marks), so it always matches the host theme. */
.ahe-card-back {
  background-color: color-mix(in srgb, var(--ui-accent) 30%, var(--ahe-felt-edge));
  background-image:
    linear-gradient(45deg, color-mix(in srgb, var(--ui-accent) 55%, white 8%) 25%, transparent 25%, transparent 75%, color-mix(in srgb, var(--ui-accent) 55%, white 8%) 75%),
    linear-gradient(45deg, color-mix(in srgb, var(--ui-accent) 55%, white 8%) 25%, transparent 25%, transparent 75%, color-mix(in srgb, var(--ui-accent) 55%, white 8%) 75%);
  background-size: 12px 12px;
  background-position: 0 0, 6px 6px;
  border: 1px solid rgba(255,255,255,0.22);
  box-shadow: 0 2px 6px rgba(0,0,0,0.35), inset 0 0 0 2px rgba(255,255,255,0.1);
}
.ahe-card-back::after {
  content: '';
  position: absolute; inset: 12%;
  border: 1.5px solid rgba(255,255,255,0.35);
  border-radius: 5px;
}
.ahe-card-slot { display: inline-flex; gap: clamp(3px, 0.8cqw, 6px); }

/* ---------- seat card ---------- */
.ahe-seat {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.5rem 0.45rem;
  border-radius: 12px;
  background: var(--ahe-seat-bg);
  border: 1px solid var(--ui-stroke-secondary);
  box-shadow: 0 2px 10px rgba(0,0,0,0.25);
  transition: box-shadow 200ms ease, border-color 200ms ease, opacity 200ms ease;
}
.ahe-seat[data-active="true"] {
  border-color: var(--ahe-glow);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--ahe-glow) 55%, transparent), 0 0 22px color-mix(in srgb, var(--ahe-glow) 45%, transparent);
}
.ahe-seat[data-winner="true"] {
  border-color: var(--ahe-win);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--ahe-win) 60%, transparent), 0 0 24px color-mix(in srgb, var(--ahe-win) 50%, transparent);
}
.ahe-seat[data-state="folded"] { opacity: 0.5; }
.ahe-seat[data-state="out"] { opacity: 0.38; filter: grayscale(0.6); }
.ahe-seat[data-dimmed="true"] { opacity: 0.55; }
.ahe-seat-top { display: flex; align-items: center; gap: 0.4rem; width: 100%; min-width: 0; }
.ahe-avatar {
  position: relative;
  flex: none;
  width: 30px; height: 30px;
  border-radius: 50%;
  display: grid; place-items: center;
  font-size: 1rem;
  background: var(--ui-bg-secondary);
  border: 1px solid var(--ui-stroke-secondary);
}
.ahe-avatar-fallback { display: grid; place-items: center; border-radius: 22%; color: white; font-size: 0.72rem; font-weight: 750; }
.ahe-seat-pos[data-slot="human"] .ahe-avatar { width: 32px; height: 32px; font-size: 1.05rem; }
.ahe-deadline-ring { position: absolute; inset: -3px; transform: rotate(-90deg); }
.ahe-deadline-ring circle { transition: stroke-dasharray 900ms linear; }
.ahe-seat-name-wrap { min-width: 0; flex: 1 1 auto; }
.ahe-seat-name { font-size: 0.78rem; font-weight: 650; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ahe-seat-sub { font-size: 0.66rem; color: var(--ui-text-tertiary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ahe-seat-stack { font-size: 0.74rem; font-weight: 600; color: var(--ui-text-secondary); }
.ahe-seat-markers {
  position: absolute; top: -8px; right: -8px;
  display: flex; flex-direction: column; gap: 3px; align-items: flex-end;
}
.ahe-seat-marker {
  font-size: 0.6rem; font-weight: 800;
  width: 19px; height: 19px; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--ahe-gold); color: #241a06;
  box-shadow: 0 1px 4px rgba(0,0,0,0.4);
}
.ahe-seat-marker[data-kind="bb"], .ahe-seat-marker[data-kind="sb"] { background: #cfd8e3; color: #12181f; }
.ahe-seat-hole { display: flex; gap: 3px; }
.ahe-seat-committed {
  position: absolute;
  bottom: -1.35rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.7rem;
  font-weight: 650;
  color: var(--ahe-glow);
  background: rgba(0,0,0,0.4);
  border-radius: 999px;
  padding: 0.05rem 0.45rem;
  white-space: nowrap;
  animation: ahe-chip-in 220ms ease both;
}
.ahe-seat-chips-row { display: flex; align-items: center; justify-content: center; gap: 0.3rem; max-width: 100%; }
.ahe-seat-award {
  position: absolute;
  top: -0.6rem;
  display: flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.72rem;
  font-weight: 750;
  color: #12240f;
  background: var(--ahe-win);
  border-radius: 999px;
  padding: 0.08rem 0.5rem;
  white-space: nowrap;
  box-shadow: 0 3px 10px rgba(0,0,0,0.35);
  animation: ahe-award-in 320ms cubic-bezier(.2,.8,.3,1) both;
  z-index: 2;
}
.ahe-token-chip {
  display: inline-flex; align-items: center; gap: 0.2rem;
  font-size: 0.6rem; color: var(--ui-text-quaternary); cursor: default;
}

/* ---------- badges ---------- */
.ahe-badge-row { display: flex; gap: 0.25rem; flex-wrap: wrap; justify-content: center; min-height: 1.1rem; width: 100%; }
.ahe-tag {
  font-size: 0.62rem;
  font-weight: 650;
  letter-spacing: 0.02em;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  white-space: nowrap;
  max-width: 100%; overflow: hidden; text-overflow: ellipsis;
}
.ahe-testbot-short { display: none; }
.ahe-tag[data-kind="thinking"] { color: var(--ui-accent); background: color-mix(in srgb, var(--ui-accent) 16%, transparent); display: inline-flex; align-items: center; gap: 0.25rem; }
.ahe-tag[data-kind="fallback"] { color: var(--ui-orange, #d99a4a); background: color-mix(in srgb, var(--ui-orange, #d99a4a) 16%, transparent); }
.ahe-tag[data-kind="error"], .ahe-tag[data-kind="disconnected"] { color: var(--ui-danger); background: color-mix(in srgb, var(--ui-danger) 16%, transparent); }
.ahe-tag[data-kind="allin"] { color: #241a06; background: var(--ahe-gold); }
.ahe-tag[data-kind="folded"] { color: var(--ui-text-quaternary); background: color-mix(in srgb, var(--ui-text-quaternary) 14%, transparent); }
.ahe-tag[data-kind="testbot"] { color: var(--ui-text-secondary); background: var(--ui-bg-secondary); border: 1px dashed var(--ui-stroke-secondary); }
.ahe-tag[data-kind="winner"] { color: #12240f; background: var(--ahe-win); }

/* ---------- talk bubbles ---------- */
.ahe-bubble {
  position: absolute;
  bottom: calc(100% + 2px);
  left: 50%;
  transform: translateX(-50%);
  max-width: 13rem;
  background: var(--ui-chat-bubble-background, var(--ui-bg-elevated));
  color: var(--ui-text-primary);
  border: 1px solid var(--ui-stroke-secondary);
  border-radius: 10px;
  padding: 0.3rem 0.55rem;
  font-size: 0.72rem;
  line-height: 1.25;
  box-shadow: 0 4px 14px rgba(0,0,0,0.3);
  animation: ahe-bubble-in 180ms ease both, ahe-bubble-out 400ms ease 3.6s forwards;
  z-index: 3;
  pointer-events: none;
}

/* ---------- betting bar ---------- */
.ahe-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  padding: 0.6rem 0.75rem;
  border-radius: 12px;
  background: var(--ui-bg-elevated);
  border: 1px solid var(--ui-stroke-secondary);
}
.ahe-bar[data-disabled="true"] { opacity: 0.6; }
.ahe-bar-actions { display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center; }
.ahe-bar-raise { display: flex; align-items: center; gap: 0.5rem; flex: 1 1 100%; flex-wrap: wrap; }
.ahe-bar-slider { flex: 1 1 140px; min-width: 140px; accent-color: var(--ui-accent); }
.ahe-bar-amount {
  width: 6rem;
  text-align: right;
  padding: 0.3rem 0.4rem;
  border-radius: 6px;
  border: 1px solid var(--ui-stroke-secondary);
  background: var(--ui-bg-input);
  color: var(--ui-text-primary);
  font-variant-numeric: tabular-nums;
  font-weight: 650;
}
.ahe-bar-quicksizes { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.ahe-bar-meta { font-size: 0.8rem; font-weight: 600; color: var(--ui-text-secondary); white-space: nowrap; }
.ahe-bar-notice {
  font-size: 0.74rem;
  color: var(--ui-danger);
  padding: 0.2rem 0.5rem;
}
.ahe-kbd-hint { display: flex; gap: 0.7rem; align-items: center; flex-wrap: wrap; color: var(--ui-text-quaternary); font-size: 0.68rem; }
.ahe-kbd-hint span { display: inline-flex; align-items: center; gap: 0.28rem; white-space: nowrap; }
.ahe-bar-pending { display: inline-flex; align-items: center; gap: 0.3rem; font-size: 0.76rem; color: var(--ui-text-tertiary); }

/* ---------- history ---------- */
.ahe-attention-banner { display: flex; align-items: center; gap: 0.45rem; padding: 0.45rem 0.7rem; border: 1px solid color-mix(in srgb, var(--ahe-gold) 55%, var(--ui-stroke-secondary)); border-radius: 9px; background: color-mix(in srgb, var(--ahe-gold) 14%, var(--ui-bg-elevated)); color: var(--ui-text-primary); font-size: 0.76rem; font-weight: 650; }
.ahe-attention-banner > span { color: #a77d20; }
.ahe-chat { border: 1px solid var(--ui-stroke-secondary); border-radius: 12px; background: var(--ui-bg-elevated); overflow: hidden; flex: 0 0 auto; }
.ahe-chat-head { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--ui-stroke-secondary); }
.ahe-chat-head > div { display: flex; align-items: baseline; gap: 0.55rem; flex-wrap: wrap; }
.ahe-chat-head strong { font-size: 0.82rem; }
.ahe-chat-head span, .ahe-chat-count { color: var(--ui-text-tertiary); font-size: 0.69rem; }
.ahe-chat-feed { height: 156px; overflow-y: auto; padding: 0.45rem 0.75rem; display: flex; flex-direction: column; gap: 0.18rem; scrollbar-width: thin; }
.ahe-chat-empty { color: var(--ui-text-tertiary); font-size: 0.76rem; margin: auto; }
.ahe-chat-line { display: flex; align-items: flex-start; gap: 0.5rem; padding: 0.28rem 0.4rem; border-radius: 7px; }
.ahe-chat-line[data-level="attention"] { background: color-mix(in srgb, var(--ahe-gold) 17%, transparent); }
.ahe-chat-line[data-kind="human"] { background: var(--ui-bg-secondary); }
.ahe-chat-avatar { width: 24px; height: 24px; flex: 0 0 24px; display: grid; place-items: center; font-size: 0.9rem; color: var(--ahe-gold); overflow: hidden; }
.ahe-chat-copy { min-width: 0; display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; }
.ahe-chat-name { color: var(--ui-text-primary); font-size: 0.73rem; font-weight: 700; white-space: nowrap; }
.ahe-chat-text { color: var(--ui-text-secondary); font-size: 0.75rem; line-height: 1.4; overflow-wrap: anywhere; }
.ahe-chat-line[data-level="attention"] .ahe-chat-text { color: var(--ui-text-primary); font-weight: 600; }
.ahe-chat-compose { display: flex; gap: 0.45rem; border-top: 1px solid var(--ui-stroke-secondary); padding: 0.5rem 0.65rem; }
.ahe-chat-compose input { flex: 1; min-width: 0; border: 1px solid var(--ui-stroke-secondary); border-radius: 7px; background: var(--ui-bg-input); color: var(--ui-text-primary); padding: 0.4rem 0.55rem; font: inherit; font-size: 0.78rem; }
.ahe-chat-compose button { border: 0; border-radius: 7px; background: var(--ui-accent); color: white; padding: 0.35rem 0.85rem; font-size: 0.75rem; font-weight: 700; cursor: pointer; }
.ahe-chat-compose button:disabled { opacity: 0.45; cursor: default; }
.ahe-chat-error { color: var(--ui-danger); font-size: 0.72rem; padding: 0 0.75rem 0.45rem; }
.ahe-history { border-radius: 10px; border: 1px solid var(--ui-stroke-secondary); background: var(--ui-bg-elevated); overflow: hidden; }
.ahe-history-head { display: flex; align-items: center; justify-content: space-between; padding: 0.4rem 0.6rem; cursor: pointer; }
.ahe-history-title { font-size: 0.78rem; font-weight: 650; }
.ahe-history-body { max-height: 220px; overflow: auto; padding: 0 0.6rem 0.5rem; }
.ahe-log-row { font-size: 0.72rem; color: var(--ui-text-secondary); padding: 0.15rem 0; border-bottom: 1px dashed var(--ui-stroke-tertiary); display: flex; gap: 0.4rem; }
.ahe-log-row:last-child { border-bottom: none; }
.ahe-log-seat { font-weight: 650; color: var(--ui-text-primary); }

/* ---------- hand-end banner ---------- */
.ahe-hand-end {
  display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap;
  padding: 0.6rem 0.85rem;
  border-radius: 12px;
  background: color-mix(in srgb, var(--ahe-win) 14%, var(--ui-bg-elevated));
  border: 1px solid color-mix(in srgb, var(--ahe-win) 45%, var(--ui-stroke-secondary));
}
.ahe-hand-end-text { font-size: 0.82rem; font-weight: 600; color: var(--ui-text-primary); }
.ahe-hand-end-sub { font-size: 0.72rem; color: var(--ui-text-tertiary); font-weight: 500; }

/* ---------- overlays (paused / finished) ---------- */
.ahe-overlay {
  position: absolute; inset: 0;
  z-index: 4;
  display: flex; align-items: center; justify-content: center;
  background: rgba(4, 12, 9, 0.62);
  border-radius: inherit;
  padding: 1rem;
}
.ahe-overlay-card {
  max-width: 26rem;
  width: 100%;
  background: var(--ui-bg-elevated);
  border: 1px solid var(--ui-stroke-secondary);
  border-radius: 14px;
  padding: 1.1rem 1.25rem;
  text-align: center;
  display: flex; flex-direction: column; align-items: center; gap: 0.6rem;
  box-shadow: 0 20px 50px rgba(0,0,0,0.4);
}
.ahe-overlay-title { font-size: 1.05rem; font-weight: 700; }
.ahe-overlay-desc { font-size: 0.82rem; color: var(--ui-text-tertiary); }

/* ---------- setup ---------- */
.ahe-setup { max-width: 900px; margin: 0 auto; width: 100%; display: flex; flex-direction: column; gap: 1.1rem; }
.ahe-setup-hero { display: flex; flex-direction: column; gap: 0.4rem; text-align: center; }
.ahe-setup-hero .ahe-live-chip { margin: 0 auto; }
.ahe-setup-tagline { font-size: 1.3rem; font-weight: 700; margin: 0.1rem 0 0; }
.ahe-setup-honest { font-size: 0.86rem; color: var(--ui-text-secondary); max-width: 40rem; margin: 0 auto; }
.ahe-rules-strip {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0.4rem 0.9rem;
  font-size: 0.74rem; color: var(--ui-text-tertiary); font-weight: 600;
  padding: 0.5rem 0.8rem; border-radius: 999px; background: var(--ui-bg-secondary);
  border: 1px solid var(--ui-stroke-secondary);
}
.ahe-rules-strip span { white-space: nowrap; }
.ahe-setup-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; }
.ahe-oppo-card { min-width: 0; border: 1px solid var(--ui-stroke-secondary); border-radius: 12px; padding: 0.85rem; background: var(--ui-bg-elevated); display: flex; flex-direction: column; gap: 0.55rem; }
.ahe-oppo-head { min-width: 0; display: flex; align-items: center; gap: 0.5rem; }
.ahe-profile-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 700; }
.ahe-oppo-head .hx-input, .ahe-oppo-head input { min-width: 0; flex: 1 1 auto; }
.ahe-field-label { font-size: 0.7rem; color: var(--ui-text-tertiary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.ahe-field { display: flex; flex-direction: column; gap: 0.25rem; min-width: 0; }
.ahe-segmented-wrap { max-width: 100%; overflow-x: auto; }
.ahe-persona-desc { font-size: 0.7rem; color: var(--ui-text-tertiary); line-height: 1.3; min-height: 1.6em; }
.ahe-model-hint { font-size: 0.68rem; color: var(--ui-text-quaternary); }
.ahe-setup-footer { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; flex-wrap: wrap; }
.ahe-avatar-row { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.ahe-avatar-pick {
  width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center;
  border: 1px solid var(--ui-stroke-secondary); background: var(--ui-bg-secondary); cursor: pointer; font-size: 0.95rem;
}
.ahe-avatar-pick[data-selected="true"] { border-color: var(--ui-accent); box-shadow: 0 0 0 2px color-mix(in srgb, var(--ui-accent) 40%, transparent); }
.ahe-inline-error { color: var(--ui-danger); font-size: 0.78rem; }
.ahe-help { color: var(--ui-text-tertiary); font-size: 0.76rem; }

/* ---------- states ---------- */
.ahe-center-state { display: flex; flex: 1 1 auto; align-items: center; justify-content: center; }
.ahe-share-row { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; }

/* ---------- narrow layout ---------- */
@container ahe (max-width: 900px) {
  .ahe-setup-grid { grid-template-columns: 1fr; }
}
@container ahe (max-width: 820px) {
  .ahe-tagline { display: none; }
  .ahe-bar-raise { flex-basis: 100%; }
}
@container ahe (max-width: 700px) {
  .ahe-seat-pos:not([data-slot="human"]) .ahe-seat-chips-row { display: none; }
  .ahe-testbot-long { display: none; }
  .ahe-testbot-short { display: inline; }
}
@container ahe (max-width: 560px) {
  .ahe-seat-pos { width: clamp(78px, 30cqw, 120px); }
  .ahe-bar-quicksizes { display: none; }
}

/* Keep the seat cards compact in a short window. The felt retains enough
   height for the board between them, and the page can scroll. */
@media (max-height: 760px) {
  .ahe-felt-wrap { min-height: 500px; }
  .ahe-felt-wrap[data-hand-ended="true"] { min-height: 550px; }
  .ahe-seat-pos[data-slot="top"] { top: 1%; }
  .ahe-seat-pos[data-slot="human"] { bottom: 1%; width: clamp(96px, 20cqw, 152px); }
  .ahe-seat-pos[data-slot="human"] .ahe-avatar { width: 28px; height: 28px; }
  .ahe-card.ahe-card-lg { width: clamp(38px, 7cqw, 56px); }
  /* Every seat card sheds its badge/style/token row here — the row most
     easily spared at a glance — to shrink its footprint enough that the
     board can clear it without the two ever fighting over the same band. */
  .ahe-seat-pos[data-slot="top"] .ahe-badge-row,
  .ahe-seat-pos[data-slot="top"] .ahe-seat-chips-row {
    display: none;
  }
  .ahe-seat-pos[data-slot="top"] .ahe-seat { padding: 0.3rem 0.4rem 0.32rem; gap: 0.2rem; }
  .ahe-board-cards { gap: 3px; }
  .ahe-board-cards .ahe-card { width: clamp(28px, 5cqw, 42px); }
}

/* In a narrow pane, a four-sided layout leaves no space for the board.
   Put opponents across the top and reserve the center for community cards. */
@container ahe (max-width: 560px) {
  .ahe-felt-wrap { flex: none; min-height: 560px; }
  .ahe-felt-wrap[data-hand-ended="true"] { min-height: 560px; }
  .ahe-seat-pos { width: min(30%, 108px); }
  .ahe-seat-pos[data-slot="left"] { left: 2%; top: 3%; transform: none; }
  .ahe-seat-pos[data-slot="top"] { left: 50%; top: 3%; transform: translateX(-50%); }
  .ahe-seat-pos[data-slot="right"] { right: 2%; top: 3%; transform: none; }
  .ahe-seat-pos[data-slot="human"] { left: 50%; bottom: 3%; width: 140px; transform: translateX(-50%); }
  .ahe-felt-inner { align-items: center; padding-top: 0; }
  .ahe-pot-row { max-width: 90cqw; }
  .ahe-bubble { top: calc(100% + 2px); bottom: auto; max-width: 100%; }
}

/* ---------- motion ---------- */
@keyframes ahe-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
@keyframes ahe-deal { from { opacity: 0; transform: translateY(-14px) scale(0.9); } to { opacity: 1; transform: translateY(0) scale(1); } }
@keyframes ahe-chip-in { from { opacity: 0; transform: translateY(6px) scale(0.8); } to { opacity: 1; transform: translateY(0) scale(1); } }
@keyframes ahe-award-in { from { opacity: 0; transform: translateY(6px) scale(0.85); } to { opacity: 1; transform: translateY(0) scale(1); } }
@keyframes ahe-bubble-in { from { opacity: 0; transform: translate(-50%, 4px) scale(0.96); } to { opacity: 1; transform: translate(-50%, 0) scale(1); } }
@keyframes ahe-bubble-out { to { opacity: 0; } }
@keyframes ahe-spin { to { transform: rotate(360deg); } }
.ahe-spin { animation: ahe-spin 900ms linear infinite; }

@media (prefers-reduced-motion: reduce) {
  .ahe-card[data-anim="deal"],
  .ahe-seat-committed,
  .ahe-seat-award,
  .ahe-bubble,
  .ahe-spin,
  .ahe-live-dot {
    animation: none !important;
  }
  .ahe-seat, .ahe-seat-pos, .ahe-deadline-ring circle { transition: none !important; }
}
`

/** Idempotent scoped-style injection (content-compare, not id-existence). */
export function ensureStyles() {
  let el = document.getElementById(STYLE_ID)
  if (!el) {
    el = document.createElement('style')
    el.id = STYLE_ID
    document.head.appendChild(el)
  }
  if (el.textContent !== CSS) el.textContent = CSS
}
