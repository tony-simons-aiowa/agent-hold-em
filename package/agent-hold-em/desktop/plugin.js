/**
 * Agent Hold 'Em — desktop plugin (built file — edit frontend/src, never this file)
 * Version: dev
 * Built:   2026-10-05T16:03:23Z
 * Build:   scripts/build-frontend.sh
 */

// frontend/src/index.jsx
import { useState as useState6 } from "react";
import {
  Button as Button4,
  ErrorState,
  GlyphSpinner as GlyphSpinner3,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  STATUSBAR_AREAS,
  host as host2,
  useQuery as useQuery3
} from "@hermes/plugin-sdk";

// frontend/src/api.js
function normalizeError(err) {
  const rawMessage = err?.message ? String(err.message) : "Request failed";
  const bridgedStatus = rawMessage.match(/(?:^|:\s)([45]\d\d):\s/);
  const status = typeof err?.statusCode === "number" ? err.statusCode : typeof err?.status === "number" ? err.status : bridgedStatus ? Number(bridgedStatus[1]) : 0;
  let code = status === 409 ? "stale" : status === 422 ? "illegal" : "error";
  let message = rawMessage;
  let legal = void 0;
  const braceIdx = message.indexOf("{");
  if (braceIdx >= 0) {
    try {
      const parsed = JSON.parse(message.slice(braceIdx));
      if (parsed && typeof parsed === "object") {
        if (typeof parsed.code === "string") code = parsed.code;
        if (typeof parsed.message === "string") message = parsed.message;
        else if (typeof parsed.detail === "string") message = parsed.detail;
        if (parsed.legal) legal = parsed.legal;
      }
    } catch {
    }
  }
  if (status === 404 && message === "Plugin not found") code = "plugin_not_found";
  return { status, code, message, legal };
}
function backendFailure(error) {
  if (error?.status === 404) {
    return {
      title: "Agent Hold 'Em isn't on this Hermes connection",
      description: "If Agent Hold 'Em is installed on this computer, choose This device in Hermes's connection switcher. Otherwise install and enable it on the selected connection. A new backend installation needs one restart."
    };
  }
  if (error?.status === 401 || error?.status === 403) {
    return {
      title: "Hermes connection needs attention",
      description: "Reconnect or sign in to the selected Hermes connection, then retry."
    };
  }
  if (!error?.status) {
    return {
      title: "Can't reach the selected Hermes backend",
      description: "Check the Hermes connection, then retry. The table will reconnect automatically when it becomes available."
    };
  }
  return {
    title: "Agent Hold 'Em couldn't load",
    description: error?.message ?? "The selected backend returned an error."
  };
}
function createApi(rest) {
  async function call(path, opts) {
    try {
      return await rest(path, opts);
    } catch (err) {
      throw normalizeError(err);
    }
  }
  return {
    /** @returns {Promise<{ok:boolean, version:string, engine:string, hermes:any}>} */
    health: () => call("/health"),
    /** @param {string} [profileId] @returns {Promise<{options: Array<{id:string,label:string,provider:string,model:string}>, default_id:string}>} */
    models: (profileId) => call(`/models${profileId ? `?profile=${encodeURIComponent(profileId)}` : ""}`),
    /** @returns {Promise<{profiles: Array<{id:string,name:string,label:string,avatar:any,model:string,provider:string}>}>} */
    profiles: () => call("/profiles"),
    /** @returns {Promise<any>} HumanView, see ARCHITECTURE.md §6 */
    state: () => call("/state"),
    /** @param {{opponents: Array<{profile_id:string,name:string,personality:string,model_id:string}>, decision_timeout_s?: number}} body */
    createTable: (body) => call("/table", { method: "POST", body }),
    /** @param {{turn_id:string, expected_version:number, client_action_id:string, kind:string, to?:number}} body */
    action: (body) => call("/action", { method: "POST", body }),
    /** @param {{text:string}} body */
    chat: (body) => call("/chat", { method: "POST", body }),
    pause: () => call("/pause", { method: "POST" }),
    resume: () => call("/resume", { method: "POST" }),
    nextHand: () => call("/next-hand", { method: "POST" }),
    /** @param {{confirm: true}} body */
    reset: (body) => call("/reset", { method: "POST", body: body ?? { confirm: true } }),
    /** @param {number} [limit] */
    history: (limit = 20) => call(`/history?limit=${encodeURIComponent(limit)}`)
  };
}
function newClientActionId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "caid-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
}

// frontend/src/styles.js
var STYLE_ID = "agent-hold-em-styles";
var CSS = `
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
  /* subtle vignette \u2014 purely decorative, sits under everything else */
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

/* seat grid \u2014 percentage-anchored positions around an oval, human bottom-center */
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
/* Original geometric card back \u2014 a diamond lattice tinted with the app's own
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
  /* Every seat card sheds its badge/style/token row here \u2014 the row most
     easily spared at a glance \u2014 to shrink its footprint enough that the
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
`;
function ensureStyles() {
  let el = document.getElementById(STYLE_ID);
  if (!el) {
    el = document.createElement("style");
    el.id = STYLE_ID;
    document.head.appendChild(el);
  }
  if (el.textContent !== CSS) el.textContent = CSS;
}

// frontend/src/components/SetupScreen.jsx
import { useEffect, useState } from "react";
import { Button, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, SegmentedControl, Tip, useQuery } from "@hermes/plugin-sdk";

// frontend/src/components/ProfileAvatar.jsx
import { Blobatar } from "@hermes/plugin-sdk";
import { jsx } from "react/jsx-runtime";
var BLOB_KIND_TRAIT = {
  round: 0.11,
  organic: 0.35,
  boxy: 0.54,
  capsule: 0.65,
  nub: 0.745,
  cloud: 0.825,
  droplet: 0.8875,
  hexagon: 0.9325,
  sun: 0.965,
  triangle: 0.99
};
function ProfileAvatar({ avatar, size = 32 }) {
  if (typeof avatar === "string") return /* @__PURE__ */ jsx("span", { children: avatar });
  if (avatar?.image_kind !== "photo" && avatar?.shape?.startsWith("blobatar")) {
    const [, pinnedSeed, kind] = avatar.shape.split(":");
    const traits = BLOB_KIND_TRAIT[kind] == null ? void 0 : { shape: BLOB_KIND_TRAIT[kind] };
    return /* @__PURE__ */ jsx(Blobatar, { name: pinnedSeed || avatar.seed || "agent", size, traits, alt: "" });
  }
  if (avatar?.image) {
    return /* @__PURE__ */ jsx("img", { src: avatar.image, alt: "", width: size, height: size, style: { display: "block", width: size, height: size, borderRadius: "22%", objectFit: "cover" } });
  }
  return /* @__PURE__ */ jsx("span", { className: "ahe-avatar-fallback", style: { width: size, height: size, background: avatar?.color || "#8b5cf6" }, children: (avatar?.seed || "?").slice(0, 1).toUpperCase() });
}

// frontend/src/components/SetupScreen.jsx
import { jsx as jsx2, jsxs } from "react/jsx-runtime";
var PERSONALITIES = [
  { id: "cautious", label: "Cautious", description: "Plays few pots, folds to pressure without a strong hand." },
  { id: "balanced", label: "Balanced", description: "Mixes it up \u2014 no obvious pattern to exploit." },
  { id: "aggressive", label: "Aggressive", description: "Bets and raises often, applies pressure early." }
];
function OpponentCard({ index, value, onChange, profiles, api: api2 }) {
  const profile = profiles.find((p) => p.id === value.profile_id);
  const personaDesc = PERSONALITIES.find((p) => p.id === value.personality)?.description;
  const modelsQuery = useQuery({
    queryKey: ["agent-hold-em", "models", value.profile_id],
    queryFn: () => api2.models(value.profile_id),
    enabled: Boolean(value.profile_id),
    staleTime: 6e4
  });
  const modelOptions = modelsQuery.data?.options ?? [];
  const [modelSearch, setModelSearch] = useState("");
  const query = modelSearch.trim().toLowerCase();
  const matchingModels = query ? modelOptions.filter((opt) => `${opt.label} ${opt.id}`.toLowerCase().includes(query)) : modelOptions;
  const selectedModel = modelOptions.find((opt) => opt.id === value.model_id);
  const visibleModels = matchingModels.slice(0, 25);
  if (selectedModel && !visibleModels.some((opt) => opt.id === selectedModel.id)) visibleModels.unshift(selectedModel);
  return /* @__PURE__ */ jsxs("div", { className: "ahe-oppo-card", children: [
    /* @__PURE__ */ jsxs("div", { className: "ahe-oppo-head", children: [
      /* @__PURE__ */ jsx2("span", { "aria-hidden": "true", children: /* @__PURE__ */ jsx2(ProfileAvatar, { avatar: profile?.avatar, size: 36 }) }),
      /* @__PURE__ */ jsx2("div", { className: "ahe-profile-name", children: profile?.name || `Opponent ${index + 1}` })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "ahe-field", children: [
      /* @__PURE__ */ jsx2("label", { className: "ahe-field-label", children: "Hermes profile" }),
      /* @__PURE__ */ jsxs(Select, { value: value.profile_id, onValueChange: (id) => {
        setModelSearch("");
        onChange({ ...value, profile_id: id, model_id: "default" });
      }, children: [
        /* @__PURE__ */ jsx2(SelectTrigger, { "aria-label": `Opponent ${index + 1} profile`, children: /* @__PURE__ */ jsx2(SelectValue, { placeholder: "Choose a profile" }) }),
        /* @__PURE__ */ jsx2(SelectContent, { children: profiles.map((p) => /* @__PURE__ */ jsx2(SelectItem, { value: p.id, children: p.label }, p.id)) })
      ] }),
      /* @__PURE__ */ jsx2("div", { className: "ahe-model-hint", children: "Uses this profile's model connection and Bot Mode identity." })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "ahe-field", children: [
      /* @__PURE__ */ jsx2("label", { className: "ahe-field-label", children: "Personality" }),
      /* @__PURE__ */ jsx2("div", { className: "ahe-segmented-wrap", children: /* @__PURE__ */ jsx2(SegmentedControl, { value: value.personality, onChange: (v) => onChange({ ...value, personality: v }), options: PERSONALITIES }) }),
      /* @__PURE__ */ jsx2("div", { className: "ahe-persona-desc", children: personaDesc })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "ahe-field", children: [
      /* @__PURE__ */ jsx2("label", { className: "ahe-field-label", children: "Model" }),
      modelOptions.length > 8 && /* @__PURE__ */ jsx2(
        Input,
        {
          "aria-label": `Search opponent ${index + 1} models`,
          value: modelSearch,
          placeholder: "Search provider or model",
          onChange: (e) => setModelSearch(e.target.value)
        }
      ),
      /* @__PURE__ */ jsxs(Select, { value: value.model_id, onValueChange: (v) => onChange({ ...value, model_id: v }), children: [
        /* @__PURE__ */ jsx2(SelectTrigger, { "aria-label": `Opponent ${index + 1} model`, children: /* @__PURE__ */ jsx2(SelectValue, { placeholder: modelsQuery.isLoading ? "Loading models\u2026" : "Choose a model" }) }),
        /* @__PURE__ */ jsx2(SelectContent, { children: visibleModels.map((opt) => /* @__PURE__ */ jsx2(SelectItem, { value: opt.id, children: opt.label }, opt.id)) })
      ] }),
      modelsQuery.isError && /* @__PURE__ */ jsx2("div", { className: "ahe-inline-error", children: "Could not load this profile's models." }),
      modelOptions.length > 8 && /* @__PURE__ */ jsx2("div", { className: "ahe-model-hint", children: matchingModels.length === 0 ? "No matching models." : `${matchingModels.length} match${matchingModels.length === 1 ? "" : "es"}${matchingModels.length > 25 ? " \u2014 showing first 25" : ""}` }),
      value.model_id === "default" && /* @__PURE__ */ jsx2("div", { className: "ahe-model-hint", children: "Uses this profile's default model." })
    ] })
  ] });
}
function SetupScreen({ profilesData, profilesError, api: api2, onSubmit, submitting, error }) {
  const profiles = profilesData?.profiles ?? [];
  const [opponents, setOpponents] = useState(() => PERSONALITIES.map((p) => ({ profile_id: "", personality: p.id, model_id: "default" })));
  const [timeout_s, setTimeoutS] = useState(20);
  useEffect(() => {
    if (!profiles.length) return;
    setOpponents((previous) => {
      const used = /* @__PURE__ */ new Set();
      return previous.map((opp) => {
        const chosen = profiles.find((p) => p.id === opp.profile_id && !used.has(p.id)) || profiles.find((p) => !used.has(p.id));
        if (chosen) used.add(chosen.id);
        return { ...opp, profile_id: chosen?.id || "" };
      });
    });
  }, [profilesData]);
  const selectedIds = opponents.map((o) => o.profile_id).filter(Boolean);
  const ready = profiles.length >= 3 && selectedIds.length === 3 && new Set(selectedIds).size === 3;
  function handleSubmit() {
    if (!ready) return;
    onSubmit({
      opponents: opponents.map((o) => ({
        profile_id: o.profile_id,
        name: profiles.find((p) => p.id === o.profile_id)?.name || o.profile_id,
        personality: o.personality,
        model_id: o.model_id
      })),
      decision_timeout_s: timeout_s
    });
  }
  return /* @__PURE__ */ jsxs("div", { className: "ahe-setup", children: [
    /* @__PURE__ */ jsxs("div", { className: "ahe-setup-hero", children: [
      /* @__PURE__ */ jsx2("span", { className: "ahe-live-chip", "data-live": "false", children: "Bring your agents to the table" }),
      /* @__PURE__ */ jsx2("p", { className: "ahe-setup-honest", children: "Choose three Hermes profiles. Their Bot Mode names and avatars come to the felt; each agent uses its own profile's model connection, with no tools or chat memory." })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "ahe-rules-strip", children: [
      /* @__PURE__ */ jsx2("span", { children: "No-Limit Hold'Em" }),
      /* @__PURE__ */ jsx2("span", { children: "1,000 chips" }),
      /* @__PURE__ */ jsx2("span", { children: "Blinds 5 / 10" }),
      /* @__PURE__ */ jsx2("span", { children: "Play chips only \u2014 no real money" })
    ] }),
    profilesError && /* @__PURE__ */ jsxs("div", { className: "ahe-inline-error", children: [
      "Could not load Hermes profiles: ",
      profilesError
    ] }),
    !profilesData && !profilesError && /* @__PURE__ */ jsx2("div", { className: "ahe-model-hint", children: "Loading Hermes profiles\u2026" }),
    profilesData && profiles.length < 3 && /* @__PURE__ */ jsx2("div", { className: "ahe-inline-error", children: "At least three local Hermes profiles are needed to start a table." }),
    /* @__PURE__ */ jsx2("div", { className: "ahe-setup-grid", children: opponents.map((o, i) => /* @__PURE__ */ jsx2(
      OpponentCard,
      {
        index: i,
        value: o,
        profiles,
        api: api2,
        onChange: (next) => setOpponents((prev) => prev.map((p, idx) => {
          if (idx === i) return next;
          if (next.profile_id !== o.profile_id && p.profile_id === next.profile_id) {
            return { ...p, profile_id: o.profile_id, model_id: "default" };
          }
          return p;
        }))
      },
      i
    )) }),
    /* @__PURE__ */ jsxs("div", { className: "ahe-setup-footer", children: [
      /* @__PURE__ */ jsxs("div", { className: "ahe-field", children: [
        /* @__PURE__ */ jsx2("label", { className: "ahe-field-label", htmlFor: "ahe-timeout", children: "Decision timeout (seconds)" }),
        /* @__PURE__ */ jsx2(Tip, { label: "How long each Hermes agent gets to decide before the table auto-folds (or checks) for it.", children: /* @__PURE__ */ jsx2(
          Input,
          {
            id: "ahe-timeout",
            type: "number",
            min: 5,
            max: 60,
            value: timeout_s,
            onChange: (e) => setTimeoutS(Number(e.target.value) || 20),
            style: { width: "6rem" }
          }
        ) })
      ] }),
      /* @__PURE__ */ jsx2(Button, { disabled: submitting || !ready, onClick: handleSubmit, children: submitting ? "Dealing you in\u2026" : "Deal me in" })
    ] }),
    error && /* @__PURE__ */ jsx2("div", { className: "ahe-inline-error", children: error })
  ] });
}

// frontend/src/components/TableScreen.jsx
import { useEffect as useEffect4, useMemo, useRef as useRef3, useState as useState5 } from "react";
import { Button as Button3, ConfirmDialog, CopyButton, StatusDot } from "@hermes/plugin-sdk";

// frontend/src/format.js
var SUIT_GLYPH = { s: "\u2660", h: "\u2665", d: "\u2666", c: "\u2663" };
var SUIT_NAME = { s: "spades", h: "hearts", d: "diamonds", c: "clubs" };
var RANK_LABEL = { T: "10" };
function parseCard(card) {
  if (!card || card.length < 2) return null;
  const rank = card[0].toUpperCase();
  const suit = card[1].toLowerCase();
  return {
    rank: RANK_LABEL[rank] ?? rank,
    suit,
    glyph: SUIT_GLYPH[suit] ?? "?",
    name: SUIT_NAME[suit] ?? "unknown",
    red: suit === "h" || suit === "d"
  };
}
function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}
function fmtChips(n) {
  if (n == null || Number.isNaN(n)) return "\u2014";
  return Math.round(n).toLocaleString("en-US");
}
function fmtPct(n) {
  if (n == null || Number.isNaN(n)) return "\u2014";
  return `${Math.round(n * 100)}%`;
}
function fmtCompact(n) {
  if (n == null || Number.isNaN(n)) return "\u2014";
  if (n < 1e3) return String(Math.round(n));
  return `${(n / 1e3).toFixed(1).replace(/\.0$/, "")}k`;
}
function secondsUntil(epochSeconds, nowMs = Date.now()) {
  if (epochSeconds == null) return null;
  return Math.max(0, epochSeconds - nowMs / 1e3);
}
function ringFraction(startedAt, deadlineAt, nowMs = Date.now()) {
  if (startedAt == null || deadlineAt == null) return null;
  const total = deadlineAt - startedAt;
  if (total <= 0) return 0;
  const remaining = deadlineAt - nowMs / 1e3;
  return clamp(remaining / total, 0, 1);
}
function styleLabel(stats) {
  if (!stats || stats.hands == null) return null;
  if (stats.hands < 8) return "Reading\u2026";
  const { vpip, pfr } = stats;
  if (vpip == null || pfr == null) return "Reading\u2026";
  if (vpip >= 0.45 && pfr >= 0.3) return "Loose-aggressive";
  if (vpip >= 0.45 && pfr < 0.3) return "Loose-passive";
  if (vpip < 0.3 && pfr >= 0.2) return "Tight-aggressive";
  if (vpip < 0.3 && pfr < 0.15) return "Tight-passive";
  return "Balanced";
}
function quickSizes(legal, totalPot) {
  if (!legal) return [];
  const { min_to, max_to } = legal;
  if (min_to == null || max_to == null) return [];
  const sizes = [
    { label: "Min", to: min_to },
    { label: "\xBD Pot", to: Math.round(totalPot * 0.5) },
    { label: "\xBE Pot", to: Math.round(totalPot * 0.75) },
    { label: "Pot", to: totalPot },
    { label: "All-in", to: max_to }
  ];
  const seen = /* @__PURE__ */ new Set();
  return sizes.map((s) => ({ ...s, to: clamp(s.to, min_to, max_to) })).filter((s) => {
    if (seen.has(s.to)) return false;
    seen.add(s.to);
    return true;
  });
}
function opponentSummaryLabel(seats) {
  const opponents = (seats ?? []).filter((s) => s.kind !== "human");
  const agents = opponents.filter((s) => s.kind === "hermes").length;
  const bots = opponents.filter((s) => s.kind === "test_bot").length;
  const parts = [];
  if (agents > 0) parts.push(`${agents} Hermes agent${agents === 1 ? "" : "s"}`);
  if (bots > 0) parts.push(`${bots} test bot${bots === 1 ? "" : "s"}`);
  return parts.join(" + ") || "No opponents";
}
function fallbackReason(seat) {
  if (seat.agent?.last_error) return "invalid reply";
  return "timeout";
}

// frontend/src/components/Card.jsx
import { jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
var FOUR_COLOR = { s: "#1a1a1a", c: "#1c7a3c", d: "#1c5fc7", h: "#c62828" };
function Card({ card, faceDown, size = "md", anim, fourColor, winning, dim }) {
  const sizeClass = size === "sm" ? " ahe-card-sm" : size === "lg" ? " ahe-card-lg" : "";
  if (faceDown || !card) {
    return /* @__PURE__ */ jsx3("div", { className: `ahe-card ahe-card-back${sizeClass}`, "data-anim": anim, "aria-hidden": "true" });
  }
  const parsed = parseCard(card);
  if (!parsed) return null;
  const style = fourColor && FOUR_COLOR[parsed.suit] ? { color: FOUR_COLOR[parsed.suit] } : void 0;
  return /* @__PURE__ */ jsxs2(
    "div",
    {
      className: `ahe-card${sizeClass}`,
      "data-red": String(parsed.red),
      "data-suit": parsed.suit,
      "data-anim": anim,
      "data-winning": winning ? "true" : void 0,
      "data-dim": dim ? "true" : void 0,
      style,
      role: "img",
      "aria-label": `${parsed.rank} of ${parsed.name}`,
      children: [
        /* @__PURE__ */ jsxs2("span", { className: "ahe-card-corner", children: [
          /* @__PURE__ */ jsx3("span", { children: parsed.rank }),
          /* @__PURE__ */ jsx3("span", { children: parsed.glyph })
        ] }),
        /* @__PURE__ */ jsx3("span", { className: "ahe-card-rank", children: parsed.rank }),
        /* @__PURE__ */ jsx3("span", { className: "ahe-card-suit", children: parsed.glyph })
      ]
    }
  );
}
function CardRow({ cards, count, faceDown, size, dealKey, fourColor, winning, dim }) {
  const n = count ?? cards?.length ?? 0;
  const slots = Array.from({ length: n }, (_, i) => i);
  return /* @__PURE__ */ jsx3("div", { className: "ahe-card-slot", children: slots.map((i) => /* @__PURE__ */ jsx3(
    Card,
    {
      card: cards?.[i],
      faceDown: faceDown || !cards?.[i],
      size,
      fourColor,
      winning,
      dim,
      anim: dealKey ? "deal" : void 0
    },
    dealKey ? `${dealKey}-${i}` : i
  )) });
}

// frontend/src/components/AgentBadge.jsx
import { GlyphSpinner, Tip as Tip2 } from "@hermes/plugin-sdk";
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function AgentBadgeRow({ seat, nowMs }) {
  const tags = [];
  const agent = seat.agent;
  const state = seat.state;
  if (agent?.state === "thinking") {
    const elapsed = agent.since != null ? Math.max(0, Math.round(nowMs / 1e3 - agent.since)) : null;
    tags.push(
      /* @__PURE__ */ jsxs3("span", { className: "ahe-tag", "data-kind": "thinking", children: [
        /* @__PURE__ */ jsx4(GlyphSpinner, { ariaLabel: "Thinking" }),
        "Thinking",
        elapsed != null ? ` \xB7 ${elapsed}s` : ""
      ] }, "thinking")
    );
  } else if (agent?.state === "error") {
    tags.push(
      /* @__PURE__ */ jsxs3("span", { className: "ahe-tag", "data-kind": "error", children: [
        "Error",
        agent.last_error ? `: ${agent.last_error}` : ""
      ] }, "error")
    );
  } else if (agent?.state === "disconnected") {
    tags.push(
      /* @__PURE__ */ jsx4("span", { className: "ahe-tag", "data-kind": "disconnected", children: "Disconnected" }, "disconnected")
    );
  }
  if (seat.last_action?.fallback) {
    const verb = seat.last_action.kind === "check" ? "Auto-checked" : "Auto-folded";
    tags.push(
      /* @__PURE__ */ jsxs3("span", { className: "ahe-tag", "data-kind": "fallback", children: [
        verb,
        " \u2014 ",
        fallbackReason(seat)
      ] }, "fallback")
    );
  }
  if (state === "folded") {
    tags.push(
      /* @__PURE__ */ jsx4("span", { className: "ahe-tag", "data-kind": "folded", children: "Folded" }, "folded")
    );
  }
  if (state === "all_in") {
    tags.push(
      /* @__PURE__ */ jsx4("span", { className: "ahe-tag", "data-kind": "allin", children: "All-in" }, "allin")
    );
  }
  if (state === "out") {
    tags.push(
      /* @__PURE__ */ jsx4("span", { className: "ahe-tag", "data-kind": "folded", children: "Out" }, "out")
    );
  }
  if (seat.kind === "test_bot") {
    tags.push(
      /* @__PURE__ */ jsxs3("span", { className: "ahe-tag", "data-kind": "testbot", children: [
        /* @__PURE__ */ jsx4("span", { className: "ahe-testbot-long", children: "TEST BOT \u2014 not an agent" }),
        /* @__PURE__ */ jsx4("span", { className: "ahe-testbot-short", children: "TEST BOT" })
      ] }, "testbot")
    );
  }
  if (tags.length === 0) return /* @__PURE__ */ jsx4("div", { className: "ahe-badge-row" });
  return /* @__PURE__ */ jsx4("div", { className: "ahe-badge-row", children: tags });
}
function StatsTooltipContent({ seat }) {
  const stats = seat.stats;
  const label = styleLabel(stats);
  return /* @__PURE__ */ jsxs3("div", { children: [
    /* @__PURE__ */ jsx4("div", { children: /* @__PURE__ */ jsx4("strong", { children: seat.model_label ?? "Unknown model" }) }),
    seat.personality ? /* @__PURE__ */ jsxs3("div", { children: [
      "Personality: ",
      seat.personality
    ] }) : null,
    label ? /* @__PURE__ */ jsxs3("div", { children: [
      "Style: ",
      label
    ] }) : null,
    stats ? /* @__PURE__ */ jsxs3("div", { children: [
      "Hands ",
      stats.hands,
      " \xB7 VPIP ",
      fmtPct(stats.vpip),
      " \xB7 PFR ",
      fmtPct(stats.pfr),
      " \xB7 AF ",
      stats.af?.toFixed?.(1) ?? "\u2014"
    ] }) : /* @__PURE__ */ jsx4("div", { children: "No hands played yet" }),
    agentTokens(seat)
  ] });
}
function agentTokens(seat) {
  const tokens = seat.agent?.tokens;
  if (!tokens) return null;
  return /* @__PURE__ */ jsxs3("div", { children: [
    "Tokens: ",
    fmtChips(tokens.total),
    " total (this table)"
  ] });
}
function StyleChip({ seat }) {
  const label = styleLabel(seat.stats);
  if (!label) return null;
  return /* @__PURE__ */ jsx4(Tip2, { label: /* @__PURE__ */ jsx4(StatsTooltipContent, { seat }), children: /* @__PURE__ */ jsx4("span", { className: "ahe-tag", "data-kind": "folded", style: { cursor: "default" }, children: label }) });
}
function TokenChip({ seat }) {
  const tokens = seat.agent?.tokens;
  if (seat.kind !== "hermes" || !tokens) return null;
  return /* @__PURE__ */ jsx4(Tip2, { label: `This Hermes agent's token usage for this table: ${fmtChips(tokens.input)} in / ${fmtChips(tokens.output)} out`, children: /* @__PURE__ */ jsxs3("span", { className: "ahe-token-chip", children: [
    /* @__PURE__ */ jsx4("span", { "aria-hidden": "true", children: "\u25C6" }),
    " ",
    fmtCompact(tokens.total),
    " tok"
  ] }) });
}

// frontend/src/components/TalkBubble.jsx
import { jsx as jsx5 } from "react/jsx-runtime";
function TalkBubble({ talk }) {
  if (!talk) return null;
  return /* @__PURE__ */ jsx5("div", { className: "ahe-bubble", role: "status", children: talk }, talk);
}

// frontend/src/components/Seat.jsx
import { jsx as jsx6, jsxs as jsxs4 } from "react/jsx-runtime";
var RING_R = 17;
var RING_C = 2 * Math.PI * RING_R;
function DeadlineRing({ startedAt, deadlineAt, nowMs, reducedMotion }) {
  const frac = ringFraction(startedAt, deadlineAt, nowMs);
  if (frac == null) return null;
  if (reducedMotion) {
    const left = Math.ceil(secondsUntil(deadlineAt, nowMs) ?? 0);
    return /* @__PURE__ */ jsxs4("span", { className: "ahe-deadline-ring", "aria-hidden": "true", style: { display: "grid", placeItems: "center", color: "var(--ui-text-secondary)", fontSize: "0.6rem", fontWeight: 700 }, children: [
      left,
      "s"
    ] });
  }
  const dash = RING_C * frac;
  return /* @__PURE__ */ jsxs4("svg", { className: "ahe-deadline-ring", width: "36", height: "36", viewBox: "0 0 36 36", "aria-hidden": "true", children: [
    /* @__PURE__ */ jsx6("circle", { cx: "18", cy: "18", r: RING_R, fill: "none", stroke: "var(--ui-stroke-secondary)", strokeWidth: "2" }),
    /* @__PURE__ */ jsx6(
      "circle",
      {
        cx: "18",
        cy: "18",
        r: RING_R,
        fill: "none",
        stroke: frac < 0.25 ? "var(--ui-danger)" : "var(--ahe-glow)",
        strokeWidth: "2",
        strokeDasharray: `${dash} ${RING_C}`,
        strokeLinecap: "round"
      }
    )
  ] });
}
function Seat({
  seat,
  isSelf,
  isToAct,
  dealerSeat,
  sbSeat,
  bbSeat,
  nowMs,
  dealKey,
  revealed,
  turnStartedAt,
  turnDeadlineAt,
  reducedMotion,
  fourColor,
  isWinner,
  isLosingReveal,
  award
}) {
  const showThinkingRing = seat.agent?.state === "thinking" && isToAct;
  const showHole = isSelf || revealed && seat.hole;
  return /* @__PURE__ */ jsxs4(
    "div",
    {
      className: "ahe-seat",
      "data-active": String(isToAct),
      "data-state": seat.state,
      "data-winner": String(Boolean(isWinner)),
      "data-dimmed": String(Boolean(isLosingReveal)),
      children: [
        /* @__PURE__ */ jsx6(TalkBubble, { talk: seat.talk }),
        award != null && /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-award", role: "status", children: [
          "+",
          fmtChips(award)
        ] }),
        /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-markers", children: [
          seat.seat === dealerSeat && /* @__PURE__ */ jsx6("span", { className: "ahe-seat-marker", "data-kind": "d", children: "D" }),
          seat.seat === sbSeat && /* @__PURE__ */ jsx6("span", { className: "ahe-seat-marker", "data-kind": "sb", children: "SB" }),
          seat.seat === bbSeat && /* @__PURE__ */ jsx6("span", { className: "ahe-seat-marker", "data-kind": "bb", children: "BB" })
        ] }),
        /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-top", children: [
          /* @__PURE__ */ jsxs4("div", { className: "ahe-avatar", "aria-hidden": "true", children: [
            showThinkingRing && /* @__PURE__ */ jsx6(DeadlineRing, { startedAt: turnStartedAt, deadlineAt: turnDeadlineAt, nowMs, reducedMotion }),
            /* @__PURE__ */ jsx6(ProfileAvatar, { avatar: seat.avatar ?? (seat.kind === "human" ? "\u{1F9D1}" : "\u{1F916}"), size: 30 })
          ] }),
          /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-name-wrap", children: [
            /* @__PURE__ */ jsx6("div", { className: "ahe-seat-name", children: seat.name }),
            /* @__PURE__ */ jsx6("div", { className: "ahe-seat-sub", children: seat.kind === "human" ? "You" : [seat.personality, seat.model_label].filter(Boolean).join(" \xB7 ") || (seat.kind === "test_bot" ? "Scripted" : "Agent") })
          ] })
        ] }),
        /* @__PURE__ */ jsx6(
          CardRow,
          {
            cards: showHole ? seat.hole : void 0,
            count: 2,
            faceDown: !showHole,
            size: isSelf ? "lg" : "sm",
            dealKey,
            fourColor,
            dim: isLosingReveal
          }
        ),
        /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-stack", children: [
          fmtChips(seat.stack),
          " chips"
        ] }),
        /* @__PURE__ */ jsx6(AgentBadgeRow, { seat, nowMs }),
        /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-chips-row", children: [
          /* @__PURE__ */ jsx6(StyleChip, { seat }),
          /* @__PURE__ */ jsx6(TokenChip, { seat })
        ] }),
        seat.hand_label && revealed ? /* @__PURE__ */ jsx6("div", { className: "ahe-tag", "data-kind": isWinner ? "winner" : "folded", children: seat.hand_label }) : null,
        seat.committed > 0 && /* @__PURE__ */ jsxs4("div", { className: "ahe-seat-committed", children: [
          /* @__PURE__ */ jsx6("span", { "aria-hidden": "true", children: "\u25CF" }),
          " ",
          fmtChips(seat.committed)
        ] }, `${seat.seat}-${seat.committed}`)
      ]
    }
  );
}

// frontend/src/components/Board.jsx
import { jsx as jsx7, jsxs as jsxs5 } from "react/jsx-runtime";
function BoardArea({ board, pots, totalPot, dealKey, fourColor }) {
  return /* @__PURE__ */ jsxs5("div", { className: "ahe-board-area", children: [
    /* @__PURE__ */ jsx7("div", { className: "ahe-board-cards", children: /* @__PURE__ */ jsx7(CardRow, { cards: board, count: Math.max(board?.length ?? 0, 0), dealKey, fourColor }) }),
    /* @__PURE__ */ jsxs5("div", { className: "ahe-pot-row", children: [
      /* @__PURE__ */ jsxs5("span", { className: "ahe-pot-chip", children: [
        "Pot ",
        fmtChips(totalPot)
      ] }),
      pots && pots.length > 1 ? pots.map((p, i) => /* @__PURE__ */ jsxs5("span", { className: "ahe-pot-chip", children: [
        "Side ",
        i + 1,
        ": ",
        fmtChips(p.amount),
        " ",
        /* @__PURE__ */ jsxs5("small", { children: [
          "(",
          p.eligible.length,
          " eligible)"
        ] })
      ] }, i)) : null
    ] })
  ] });
}

// frontend/src/components/BettingBar.jsx
import { Badge, Button as Button2, GlyphSpinner as GlyphSpinner2, Kbd } from "@hermes/plugin-sdk";
import { jsx as jsx8, jsxs as jsxs6 } from "react/jsx-runtime";
function BettingBar({ legal, totalPot, bb, pending, notice, raiseInputRef, raiseTo, onRaiseToChange, onAct }) {
  if (!legal) return null;
  const canRaise = Boolean(legal.raise_kind);
  const raiseWord = legal.raise_kind === "bet" ? "Bet" : "Raise to";
  const sizes = canRaise ? quickSizes(legal, totalPot) : [];
  const amount = raiseTo ?? legal.min_to ?? 0;
  function setClamped(v) {
    if (legal.min_to == null || legal.max_to == null) return;
    onRaiseToChange(clamp(Math.round(v), legal.min_to, legal.max_to));
  }
  function submitRaise() {
    onAct(legal.raise_kind, amount);
  }
  return /* @__PURE__ */ jsxs6("div", { className: "ahe-bar", "data-disabled": String(pending), role: "group", "aria-label": "Betting actions", children: [
    /* @__PURE__ */ jsxs6("div", { className: "ahe-bar-actions", children: [
      legal.can_fold && /* @__PURE__ */ jsx8(Button2, { variant: "outline", disabled: pending, onClick: () => onAct("fold"), children: "Fold" }),
      legal.can_check && /* @__PURE__ */ jsx8(Button2, { disabled: pending, onClick: () => onAct("check"), children: "Check" }),
      legal.can_call && /* @__PURE__ */ jsxs6(Button2, { disabled: pending, onClick: () => onAct("call"), children: [
        "Call ",
        fmtChips(legal.call_amount)
      ] }),
      pending && /* @__PURE__ */ jsxs6("span", { className: "ahe-bar-pending", role: "status", children: [
        /* @__PURE__ */ jsx8(GlyphSpinner2, { ariaLabel: "Sending" }),
        " Sending\u2026"
      ] })
    ] }),
    canRaise && /* @__PURE__ */ jsxs6("div", { className: "ahe-bar-raise", children: [
      /* @__PURE__ */ jsx8(
        "input",
        {
          ref: raiseInputRef,
          className: "ahe-bar-amount",
          type: "number",
          min: legal.min_to,
          max: legal.max_to,
          step: bb,
          value: amount,
          disabled: pending,
          "aria-label": `${raiseWord} amount`,
          onChange: (e) => setClamped(Number(e.target.value))
        }
      ),
      /* @__PURE__ */ jsx8(
        "input",
        {
          className: "ahe-bar-slider",
          type: "range",
          min: legal.min_to,
          max: legal.max_to,
          step: 1,
          value: amount,
          disabled: pending,
          "aria-label": `${raiseWord} slider`,
          onChange: (e) => setClamped(Number(e.target.value))
        }
      ),
      /* @__PURE__ */ jsx8("div", { className: "ahe-bar-quicksizes", children: sizes.map((s) => /* @__PURE__ */ jsx8(Button2, { size: "sm", variant: "ghost", disabled: pending, onClick: () => setClamped(s.to), children: s.label }, s.label)) }),
      /* @__PURE__ */ jsxs6(Button2, { disabled: pending, onClick: submitRaise, children: [
        raiseWord,
        " ",
        fmtChips(amount)
      ] })
    ] }),
    /* @__PURE__ */ jsxs6("div", { className: "ahe-bar-meta", children: [
      "To call ",
      fmtChips(legal.to_call),
      " \xB7 Stack ",
      fmtChips(legal.stack)
    ] }),
    notice && /* @__PURE__ */ jsx8(Badge, { variant: "destructive", className: "ahe-bar-notice", children: notice }),
    /* @__PURE__ */ jsxs6("div", { className: "ahe-kbd-hint", "aria-hidden": "true", children: [
      /* @__PURE__ */ jsxs6("span", { children: [
        /* @__PURE__ */ jsx8(Kbd, { children: "F" }),
        " Fold"
      ] }),
      /* @__PURE__ */ jsxs6("span", { children: [
        /* @__PURE__ */ jsx8(Kbd, { children: "C" }),
        " Check/Call"
      ] }),
      /* @__PURE__ */ jsxs6("span", { children: [
        /* @__PURE__ */ jsx8(Kbd, { children: "R" }),
        " Raise"
      ] }),
      /* @__PURE__ */ jsxs6("span", { children: [
        /* @__PURE__ */ jsx8(Kbd, { children: "\u2191\u2193" }),
        " \xB1BB"
      ] }),
      /* @__PURE__ */ jsxs6("span", { children: [
        /* @__PURE__ */ jsx8(Kbd, { children: "A" }),
        " All-in"
      ] }),
      /* @__PURE__ */ jsxs6("span", { children: [
        /* @__PURE__ */ jsx8(Kbd, { children: "Enter" }),
        " Confirm"
      ] })
    ] })
  ] });
}

// frontend/src/components/HistoryPanel.jsx
import { useState as useState2 } from "react";
import { Codicon, ScrollArea } from "@hermes/plugin-sdk";
import { jsx as jsx9, jsxs as jsxs7 } from "react/jsx-runtime";
function describeEvent(ev) {
  switch (ev.type ?? ev.kind) {
    case "hand_start":
      return `Hand #${ev.hand_no} \u2014 new deal`;
    case "blinds":
      return `Blinds posted`;
    case "street":
      return `${ev.name?.toUpperCase?.() ?? "Street"}${ev.board ? ` \u2014 ${ev.board.join(" ")}` : ""}`;
    case "action":
      return `${ev.kind}${ev.to != null ? ` to ${fmtChips(ev.to)}` : ""}`;
    case "uncalled_return":
      return `Uncalled ${fmtChips(ev.amount)} returned`;
    case "showdown":
      return "Showdown";
    case "pot_award":
      return `Pot ${fmtChips(ev.amount)} awarded${ev.split ? " (split)" : ""}`;
    case "bust":
      return "Busted out";
    case "hand_end":
      return "Hand ended";
    case "table_over":
      return "Table over";
    default:
      return ev.type ?? ev.kind ?? "Event";
  }
}
function HistoryPanel({ log, seatsByNo }) {
  const [open, setOpen] = useState2(false);
  return /* @__PURE__ */ jsxs7("div", { className: "ahe-history", children: [
    /* @__PURE__ */ jsxs7(
      "div",
      {
        className: "ahe-history-head",
        role: "button",
        tabIndex: 0,
        "aria-expanded": open,
        onClick: () => setOpen((o) => !o),
        onKeyDown: (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen((o) => !o);
          }
        },
        children: [
          /* @__PURE__ */ jsx9("span", { className: "ahe-history-title", children: "Hand history" }),
          /* @__PURE__ */ jsx9(Codicon, { name: open ? "chevron-up" : "chevron-down" })
        ]
      }
    ),
    open && /* @__PURE__ */ jsxs7(ScrollArea, { className: "ahe-history-body", children: [
      (!log || log.length === 0) && /* @__PURE__ */ jsx9("div", { className: "ahe-log-row", children: "No events yet." }),
      log?.map((ev, i) => /* @__PURE__ */ jsxs7("div", { className: "ahe-log-row", children: [
        ev.seat != null && seatsByNo?.[ev.seat] && /* @__PURE__ */ jsx9("span", { className: "ahe-log-seat", children: seatsByNo[ev.seat] }),
        /* @__PURE__ */ jsx9("span", { children: describeEvent(ev) })
      ] }, i))
    ] })
  ] });
}

// frontend/src/components/TableChat.jsx
import { useEffect as useEffect3, useRef as useRef2, useState as useState4 } from "react";
import { useQueryClient as useQueryClient2 } from "@hermes/plugin-sdk";

// frontend/src/hooks.js
import { useEffect as useEffect2, useRef, useState as useState3 } from "react";
import { host, useQuery as useQuery2, useQueryClient } from "@hermes/plugin-sdk";
var STATE_QUERY_KEY = ["agent-hold-em", "state"];
var REFETCH_MS = 2500;
function useTableState(api2) {
  const client = useQueryClient();
  const query = useQuery2({
    queryKey: STATE_QUERY_KEY,
    queryFn: () => api2.state(),
    refetchInterval: (query2) => query2.state.status === "error" ? 15e3 : REFETCH_MS,
    retry: false
  });
  useEffect2(() => {
    return host.onEvent("plugin.agent-hold-em.table.changed", () => {
      client.invalidateQueries({ queryKey: STATE_QUERY_KEY });
    });
  }, [client]);
  return query;
}
function useNow(intervalMs = 1e3) {
  const [now, setNow] = useState3(() => Date.now());
  useEffect2(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState3(
    () => typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)").matches : false
  );
  useEffect2(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);
  return reduced;
}
function useBettingShortcuts({ containerRef, legal, bb, onFold, onCheckCall, onFocusRaise, onAdjust, onSubmit, onAllIn }) {
  const stateRef = useRef({ legal, bb, onFold, onCheckCall, onFocusRaise, onAdjust, onSubmit, onAllIn });
  stateRef.current = { legal, bb, onFold, onCheckCall, onFocusRaise, onAdjust, onSubmit, onAllIn };
  useEffect2(() => {
    function isTypingTarget(el) {
      if (!el) return false;
      const tag = el.tagName;
      return tag === "INPUT" || tag === "TEXTAREA" || el.isContentEditable;
    }
    function onKeyDown(e) {
      const s = stateRef.current;
      if (!s.legal) return;
      const root = containerRef.current;
      if (!root) return;
      if (!root.contains(document.activeElement) && document.activeElement !== document.body) return;
      if (isTypingTarget(document.activeElement) && e.key !== "Enter" && e.key !== "Escape") return;
      switch (e.key) {
        case "f":
        case "F":
          if (s.legal.can_fold) {
            e.preventDefault();
            s.onFold();
          }
          break;
        case "c":
        case "C":
          if (s.legal.can_check || s.legal.can_call) {
            e.preventDefault();
            s.onCheckCall();
          }
          break;
        case "r":
        case "R":
          if (s.legal.raise_kind) {
            e.preventDefault();
            s.onFocusRaise();
          }
          break;
        case "ArrowUp":
          if (s.legal.raise_kind) {
            e.preventDefault();
            s.onAdjust(s.bb);
          }
          break;
        case "ArrowDown":
          if (s.legal.raise_kind) {
            e.preventDefault();
            s.onAdjust(-s.bb);
          }
          break;
        case "a":
        case "A":
          if (s.legal.raise_kind) {
            e.preventDefault();
            s.onAllIn();
          }
          break;
        case "Enter":
          if (isTypingTarget(document.activeElement)) {
            e.preventDefault();
            s.onSubmit();
          }
          break;
        default:
          break;
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [containerRef]);
}

// frontend/src/components/TableChat.jsx
import { jsx as jsx10, jsxs as jsxs8 } from "react/jsx-runtime";
function TableChat({ api: api2, view, onError }) {
  const [draft, setDraft] = useState4("");
  const [sending, setSending] = useState4(false);
  const [error, setError] = useState4("");
  const feedRef = useRef2(null);
  const queryClient = useQueryClient2();
  const messages = view.chat ?? [];
  const lastId = messages.at(-1)?.id;
  const seats = Object.fromEntries(view.seats.map((seat) => [seat.seat, seat]));
  useEffect3(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [lastId]);
  async function send(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    setError("");
    try {
      const nextView = await api2.chat({ text });
      queryClient.setQueryData(STATE_QUERY_KEY, (current) => {
        if (!current) return nextView;
        if (nextView.version > current.version) return nextView;
        if (nextView.version === current.version && (nextView.chat?.length ?? 0) > (current.chat?.length ?? 0)) return nextView;
        return current;
      });
      setDraft("");
    } catch (err) {
      setError(err.message ?? "Could not send your message.");
      onError?.(err);
    } finally {
      setSending(false);
    }
  }
  return /* @__PURE__ */ jsxs8("section", { className: "ahe-chat", "aria-label": "Table chat", children: [
    /* @__PURE__ */ jsxs8("div", { className: "ahe-chat-head", children: [
      /* @__PURE__ */ jsxs8("div", { children: [
        /* @__PURE__ */ jsx10("strong", { children: "Table chat" }),
        /* @__PURE__ */ jsx10("span", { children: "Agents speak as they play \xB7 replies come on their turns" })
      ] }),
      /* @__PURE__ */ jsxs8("span", { className: "ahe-chat-count", children: [
        messages.length,
        " messages"
      ] })
    ] }),
    /* @__PURE__ */ jsxs8("div", { className: "ahe-chat-feed", ref: feedRef, role: "log", "aria-live": "polite", "aria-relevant": "additions", children: [
      messages.length === 0 && /* @__PURE__ */ jsx10("p", { className: "ahe-chat-empty", children: "The table is quiet. Say something to get it started." }),
      messages.map((msg) => {
        const seat = seats[msg.seat];
        return /* @__PURE__ */ jsxs8("div", { className: "ahe-chat-line", "data-kind": msg.kind, "data-level": msg.level ?? "info", children: [
          /* @__PURE__ */ jsx10("span", { className: "ahe-chat-avatar", "aria-hidden": "true", children: msg.kind === "system" ? "\u2726" : /* @__PURE__ */ jsx10(ProfileAvatar, { avatar: seat?.avatar, size: 24 }) }),
          /* @__PURE__ */ jsxs8("div", { className: "ahe-chat-copy", children: [
            /* @__PURE__ */ jsx10("span", { className: "ahe-chat-name", children: msg.kind === "system" ? "Table" : seat?.name ?? (msg.kind === "human" ? "You" : "Agent") }),
            /* @__PURE__ */ jsx10("span", { className: "ahe-chat-text", children: msg.text })
          ] })
        ] }, msg.id);
      })
    ] }),
    /* @__PURE__ */ jsxs8("form", { className: "ahe-chat-compose", onSubmit: send, children: [
      /* @__PURE__ */ jsx10(
        "input",
        {
          type: "text",
          value: draft,
          onChange: (event) => setDraft(event.target.value),
          onKeyDown: (event) => event.stopPropagation(),
          maxLength: 160,
          disabled: view.status === "finished" || sending,
          "aria-label": "Message the table",
          placeholder: "Talk to the table\u2026"
        }
      ),
      /* @__PURE__ */ jsx10("button", { type: "submit", disabled: !draft.trim() || sending || view.status === "finished", children: "Send" })
    ] }),
    error && /* @__PURE__ */ jsx10("div", { className: "ahe-chat-error", role: "alert", children: error })
  ] });
}

// frontend/src/components/TableScreen.jsx
import { jsx as jsx11, jsxs as jsxs9 } from "react/jsx-runtime";
var SLOT_ORDER = ["human", "left", "top", "right"];
var DECK_STORAGE_KEY = "four-color-deck";
function layoutSeats(seats, selfSeat) {
  const n = seats.length;
  const ordered = [];
  for (let i = 0; i < n; i++) {
    ordered.push(seats[(selfSeat + i) % n]);
  }
  return ordered.map((seat, i) => ({ seat, slot: SLOT_ORDER[i] ?? `extra-${i}` }));
}
function buildHandSummary(view) {
  const board = view.board?.join(" ") ?? "";
  const winners = view.last_hand?.winners;
  const seatsByNo = Object.fromEntries(view.seats.map((s) => [s.seat, s.name]));
  const winnerNames = winners?.map((w) => seatsByNo[w] ?? `seat ${w}`).join(", ");
  return `Agent Hold 'Em \u2014 Hand #${view.last_hand?.hand_no ?? view.hand_no}
Board: ${board || "(preflop)"}
Pot: ${fmtChips(
    view.last_hand?.total_pot ?? view.total_pot
  )}${winnerNames ? `
Winner(s): ${winnerNames}` : ""}`;
}
function computeAwards(log) {
  const awards = {};
  if (!Array.isArray(log)) return awards;
  for (let i = log.length - 1; i >= 0; i--) {
    const ev = log[i];
    const type = ev.type ?? ev.kind;
    if (type === "hand_start") break;
    if (type === "pot_award" && Array.isArray(ev.winners) && ev.winners.length && typeof ev.amount === "number") {
      const share = ev.amount / ev.winners.length;
      for (const w of ev.winners) awards[w] = (awards[w] ?? 0) + share;
    }
  }
  return awards;
}
function TableScreen({ api: api2, view, storage: storage2, onError }) {
  const containerRef = useRef3(null);
  const raiseInputRef = useRef3(null);
  const now = useNow(1e3);
  const reducedMotion = usePrefersReducedMotion();
  const [pending, setPending] = useState5(false);
  const [notice, setNotice] = useState5(null);
  const [confirmNewTable, setConfirmNewTable] = useState5(false);
  const [raiseTo, setRaiseTo] = useState5(null);
  const [fourColor, setFourColor] = useState5(() => {
    try {
      return Boolean(storage2?.get?.(DECK_STORAGE_KEY, false));
    } catch {
      return false;
    }
  });
  const selfSeat = view.seats.find((s) => s.kind === "human")?.seat ?? 0;
  const laid = useMemo(() => layoutSeats(view.seats, selfSeat), [view.seats, selfSeat]);
  const seatsByNo = useMemo(() => Object.fromEntries(view.seats.map((s) => [s.seat, s.name])), [view.seats]);
  const legal = view.status === "running" && view.to_act === selfSeat ? view.legal : null;
  useEffect4(() => {
    if (legal?.min_to != null) setRaiseTo(legal.min_to);
  }, [legal?.seat, legal?.min_to, legal?.max_to]);
  function toggleFourColor() {
    setFourColor((v) => {
      const next = !v;
      try {
        storage2?.set?.(DECK_STORAGE_KEY, next);
      } catch {
      }
      return next;
    });
  }
  async function act(kind, to) {
    if (!legal || pending) return;
    setPending(true);
    setNotice(null);
    try {
      await api2.action({
        turn_id: view.turn_id,
        expected_version: view.version,
        client_action_id: newClientActionId(),
        kind,
        to
      });
    } catch (err) {
      if (err.code === "stale" || err.code === "illegal" || err.code === "not_your_turn" || err.code === "duplicate") {
        setNotice("The table moved on \u2014 refreshing the state.");
      } else {
        setNotice(err.message ?? "Action failed.");
      }
      onError?.(err);
    } finally {
      setPending(false);
    }
  }
  useBettingShortcuts({
    containerRef,
    legal,
    bb: view.blinds?.bb ?? 10,
    onFold: () => act("fold"),
    onCheckCall: () => act(legal?.can_call ? "call" : "check"),
    onFocusRaise: () => raiseInputRef.current?.focus(),
    onAdjust: (delta) => {
      if (legal?.min_to == null || legal?.max_to == null) return;
      setRaiseTo((prev) => clamp((prev ?? legal.min_to) + delta, legal.min_to, legal.max_to));
    },
    onSubmit: () => {
      if (legal?.raise_kind && raiseTo != null) act(legal.raise_kind, raiseTo);
    },
    // Spec: "A" stages an all-in TO amount, Enter still confirms it — never
    // submits by itself, so a stray keypress can never shove the stack.
    onAllIn: () => legal?.max_to != null && setRaiseTo(legal.max_to)
  });
  const dealKey = `${view.hand_no}-${view.street}`;
  const deadlineSecs = secondsUntil(view.turn_deadline_at, now);
  const nextHandSecs = secondsUntil(view.next_hand_at, now);
  const handEnded = view.street === "complete" || view.street === "showdown";
  const awards = useMemo(() => handEnded ? computeAwards(view.log) : {}, [handEnded, view.log]);
  const winnerSeats = useMemo(() => {
    const fromAwards = Object.keys(awards).map(Number);
    if (fromAwards.length) return new Set(fromAwards);
    return new Set(view.last_hand?.winners ?? []);
  }, [awards, view.last_hand]);
  const liveLabel = opponentSummaryLabel(view.seats);
  const isLive = view.status === "running";
  const statusWord = view.status === "running" ? "LIVE" : view.status === "paused" ? "PAUSED" : view.status === "finished" ? "FINISHED" : view.status.toUpperCase();
  const finishedWinner = view.status === "finished" ? view.seats.find((s) => s.state !== "out") : null;
  const disconnectedNames = view.seats.filter((s) => s.agent?.state === "disconnected").map((s) => s.name);
  const attentionText = view.status === "paused" ? "Table paused \u2014 resume when you\u2019re ready." : legal ? "Your turn \u2014 choose an action below the table." : disconnectedNames.length ? `${disconnectedNames.join(", ")} lost the model connection. The table is using safe fallback moves.` : null;
  return /* @__PURE__ */ jsxs9("div", { className: "ahe-root", ref: containerRef, children: [
    /* @__PURE__ */ jsxs9("div", { className: "ahe-header", children: [
      /* @__PURE__ */ jsxs9("div", { className: "ahe-header-left", children: [
        /* @__PURE__ */ jsxs9("span", { className: "ahe-live-chip", "data-live": String(isLive), children: [
          /* @__PURE__ */ jsx11("span", { className: "ahe-live-dot", style: { animationPlayState: isLive ? "running" : "paused" } }),
          " ",
          statusWord,
          " \xB7 ",
          liveLabel
        ] }),
        /* @__PURE__ */ jsx11("span", { className: "ahe-tagline", children: "Bring your agent to the table." })
      ] }),
      /* @__PURE__ */ jsxs9("div", { className: "ahe-header-right", children: [
        /* @__PURE__ */ jsx11(StatusDot, { tone: view.status === "running" ? "good" : view.status === "paused" ? "warn" : "muted" }),
        /* @__PURE__ */ jsxs9("span", { children: [
          "Hand #",
          view.hand_no
        ] }),
        /* @__PURE__ */ jsx11("button", { type: "button", className: "ahe-deck-toggle", "data-on": String(fourColor), onClick: toggleFourColor, "aria-pressed": fourColor, children: "4-color deck" }),
        view.status === "running" && /* @__PURE__ */ jsx11(Button3, { size: "sm", variant: "outline", onClick: () => api2.pause().catch(onError), children: "Pause" }),
        view.status === "paused" && /* @__PURE__ */ jsx11(Button3, { size: "sm", onClick: () => api2.resume().catch(onError), children: "Resume" }),
        /* @__PURE__ */ jsx11(CopyButton, { text: () => buildHandSummary(view), label: "Copy hand", showLabel: true, buttonVariant: "outline", buttonSize: "sm" }),
        /* @__PURE__ */ jsx11(Button3, { size: "sm", variant: "ghost", onClick: () => setConfirmNewTable(true), children: "New table" })
      ] })
    ] }),
    attentionText && /* @__PURE__ */ jsxs9("div", { className: "ahe-attention-banner", role: "status", children: [
      /* @__PURE__ */ jsx11("span", { "aria-hidden": "true", children: "\u2726" }),
      attentionText
    ] }),
    /* @__PURE__ */ jsx11("div", { className: "ahe-felt-wrap", "data-hand-ended": String(handEnded), children: /* @__PURE__ */ jsxs9("div", { className: "ahe-felt", children: [
      /* @__PURE__ */ jsx11("div", { className: "ahe-felt-inner", children: /* @__PURE__ */ jsx11(BoardArea, { board: view.board, pots: view.pots, totalPot: view.total_pot, dealKey, fourColor }) }),
      laid.map(({ seat, slot }) => {
        const isWinner = handEnded && winnerSeats.has(seat.seat);
        const isLosingReveal = handEnded && Boolean(seat.hole) && !isWinner && seat.seat !== selfSeat;
        return /* @__PURE__ */ jsx11("div", { className: "ahe-seat-pos", "data-slot": slot, children: /* @__PURE__ */ jsx11(
          Seat,
          {
            seat,
            isSelf: seat.seat === selfSeat,
            isToAct: view.to_act === seat.seat && view.status === "running",
            dealerSeat: view.button,
            sbSeat: view.sb_seat,
            bbSeat: view.bb_seat,
            nowMs: now,
            dealKey,
            revealed: handEnded,
            turnStartedAt: view.turn_started_at,
            turnDeadlineAt: view.turn_deadline_at,
            reducedMotion,
            fourColor,
            isWinner,
            isLosingReveal,
            award: isWinner && awards[seat.seat] != null ? awards[seat.seat] : null
          }
        ) }, seat.seat);
      }),
      view.status === "paused" && /* @__PURE__ */ jsx11("div", { className: "ahe-overlay", children: /* @__PURE__ */ jsxs9("div", { className: "ahe-overlay-card", children: [
        /* @__PURE__ */ jsx11("div", { className: "ahe-overlay-title", children: "Table paused" }),
        /* @__PURE__ */ jsx11("div", { className: "ahe-overlay-desc", children: view.pause_reason === "restored" ? "Restored \u2014 paused so no tokens are spent until you resume." : "No agent will act until you resume." }),
        /* @__PURE__ */ jsx11(Button3, { onClick: () => api2.resume().catch(onError), children: "Resume" })
      ] }) }),
      view.status === "finished" && /* @__PURE__ */ jsx11("div", { className: "ahe-overlay", children: /* @__PURE__ */ jsxs9("div", { className: "ahe-overlay-card", children: [
        /* @__PURE__ */ jsx11("div", { className: "ahe-overlay-title", children: finishedWinner ? `${finishedWinner.name} wins the table` : "Table finished" }),
        /* @__PURE__ */ jsx11("div", { className: "ahe-overlay-desc", children: finishedWinner ? `${fmtChips(finishedWinner.stack)} chips \u2014 everyone else busted out.` : "This table has ended." }),
        /* @__PURE__ */ jsx11(Button3, { onClick: () => setConfirmNewTable(true), children: "New table" })
      ] }) })
    ] }) }),
    handEnded && view.status === "running" && /* @__PURE__ */ jsxs9("div", { className: "ahe-hand-end", role: "status", children: [
      /* @__PURE__ */ jsx11("span", { className: "ahe-hand-end-text", children: winnerSeats.size > 0 ? `Hand #${view.last_hand?.hand_no ?? view.hand_no} \u2014 ${[...winnerSeats].map((w) => seatsByNo[w] ?? `seat ${w}`).join(", ")} won ${fmtChips(
        view.last_hand?.total_pot ?? view.total_pot
      )}` : `Hand #${view.last_hand?.hand_no ?? view.hand_no} ended` }),
      /* @__PURE__ */ jsx11("span", { className: "ahe-hand-end-sub", children: nextHandSecs != null ? `Next hand in ${Math.ceil(nextHandSecs)}s` : "" }),
      /* @__PURE__ */ jsx11(Button3, { size: "sm", onClick: () => api2.nextHand().catch(onError), children: "Next hand" })
    ] }),
    legal ? /* @__PURE__ */ jsx11(
      BettingBar,
      {
        legal,
        totalPot: view.total_pot,
        bb: view.blinds?.bb ?? 10,
        pending,
        notice,
        raiseInputRef,
        raiseTo,
        onRaiseToChange: setRaiseTo,
        onAct: act
      }
    ) : /* @__PURE__ */ jsx11("div", { className: "ahe-bar", "data-disabled": "true", "aria-live": "polite", children: /* @__PURE__ */ jsx11("span", { role: "status", children: view.status === "finished" ? "Table finished." : view.status === "paused" ? "Paused." : view.to_act == null ? handEnded ? "Hand complete \u2014 settling up\u2026" : "Dealing\u2026" : seatsByNo[view.to_act] != null ? deadlineSecs != null ? `Waiting on ${seatsByNo[view.to_act]} \xB7 ${Math.ceil(deadlineSecs)}s left` : `Waiting on ${seatsByNo[view.to_act]}\u2026` : "Waiting\u2026" }) }),
    /* @__PURE__ */ jsx11("div", { role: "status", "aria-live": "polite", style: { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }, children: view.status === "running" && view.to_act != null ? `${seatsByNo[view.to_act] ?? `Seat ${view.to_act}`} to act` : view.status }),
    /* @__PURE__ */ jsx11(TableChat, { api: api2, view, onError }),
    /* @__PURE__ */ jsx11(HistoryPanel, { log: view.log, seatsByNo }),
    /* @__PURE__ */ jsx11(
      ConfirmDialog,
      {
        open: confirmNewTable,
        onOpenChange: setConfirmNewTable,
        title: "Start a new table?",
        description: "This ends the current table and returns everyone to setup. Chip counts reset.",
        confirmLabel: "New table",
        destructive: true,
        onConfirm: () => api2.reset({ confirm: true }).catch(onError)
      }
    )
  ] });
}

// frontend/src/index.jsx
import { jsx as jsx12, jsxs as jsxs10 } from "react/jsx-runtime";
var ID = "agent-hold-em";
var PATH = "/agent-hold-em";
var api = null;
var storage = null;
function Page() {
  const [globalError, setGlobalError] = useState6(null);
  const stateQuery = useTableState(api);
  const profilesQuery = useQuery3({
    queryKey: ["agent-hold-em", "profiles"],
    queryFn: () => api.profiles(),
    enabled: stateQuery.isSuccess && stateQuery.data?.status === "setup",
    staleTime: 6e4
  });
  const [creating, setCreating] = useState6(false);
  const [createError, setCreateError] = useState6(null);
  if (stateQuery.isLoading) {
    return /* @__PURE__ */ jsx12("div", { className: "ahe-root", children: /* @__PURE__ */ jsx12("div", { className: "ahe-center-state", children: /* @__PURE__ */ jsx12(GlyphSpinner3, { ariaLabel: "Loading Agent Hold 'Em" }) }) });
  }
  if (stateQuery.isError) {
    const failure = backendFailure(stateQuery.error);
    return /* @__PURE__ */ jsx12("div", { className: "ahe-root", children: /* @__PURE__ */ jsx12("div", { className: "ahe-center-state", children: /* @__PURE__ */ jsx12(
      ErrorState,
      {
        title: failure.title,
        description: failure.description,
        children: /* @__PURE__ */ jsx12(Button4, { onClick: () => stateQuery.refetch(), children: "Retry" })
      }
    ) }) });
  }
  const view = stateQuery.data;
  if (!view || view.status === "setup") {
    return /* @__PURE__ */ jsx12("div", { className: "ahe-root", children: /* @__PURE__ */ jsx12(
      SetupScreen,
      {
        profilesData: profilesQuery.data,
        profilesError: profilesQuery.isError ? profilesQuery.error?.message : null,
        api,
        submitting: creating,
        error: createError,
        onSubmit: async (body) => {
          setCreating(true);
          setCreateError(null);
          try {
            await api.createTable(body);
            await stateQuery.refetch();
          } catch (err) {
            setCreateError(err.message ?? "Could not start the table.");
          } finally {
            setCreating(false);
          }
        }
      }
    ) });
  }
  return /* @__PURE__ */ jsx12(TableScreen, { api, view, storage, onError: (e) => setGlobalError(e?.message) });
}
function StatusChip() {
  const query = useQuery3({
    queryKey: ["agent-hold-em", "state"],
    queryFn: () => api.state(),
    refetchInterval: (query2) => query2.state.status === "error" ? 3e4 : 5e3,
    enabled: api != null
  });
  const view = query.data;
  if (!view || view.status !== "running") return null;
  return /* @__PURE__ */ jsxs10("span", { children: [
    "\u2660 Hand ",
    view.hand_no,
    " \xB7 ",
    view.to_act === view.seats.find((s) => s.kind === "human")?.seat ? "Your turn" : "Agents playing"
  ] });
}
var plugin = {
  id: ID,
  name: "Agent Hold 'Em",
  description: "Play No-Limit Hold'Em against three real Hermes agents.",
  register(ctx) {
    api = createApi(ctx.rest);
    storage = ctx.storage;
    ensureStyles();
    ctx.registerMany([
      { id: "page", area: ROUTES_AREA, data: { path: PATH }, render: () => /* @__PURE__ */ jsx12(Page, {}) },
      {
        id: "nav",
        area: SIDEBAR_NAV_AREA,
        data: { path: PATH, label: "Agent Hold 'Em", codicon: "game" }
      },
      {
        id: "open",
        area: PALETTE_AREA,
        data: {
          id: "agent-hold-em.open",
          label: "Agent Hold 'Em: Open table",
          keywords: ["poker", "holdem", "agent", "hermes", "cards"],
          run: () => host2.navigate(PATH)
        }
      },
      {
        id: "pause-resume",
        area: PALETTE_AREA,
        data: {
          id: "agent-hold-em.pause-resume",
          label: "Agent Hold 'Em: Pause/Resume table",
          keywords: ["poker", "pause", "resume"],
          run: async () => {
            const view = await api.state();
            if (view.status === "running") await api.pause();
            else if (view.status === "paused") await api.resume();
          }
        }
      },
      {
        id: "new-table",
        area: PALETTE_AREA,
        data: {
          id: "agent-hold-em.new-table",
          label: "Agent Hold 'Em: New table",
          keywords: ["poker", "reset", "new game"],
          run: () => api.reset({ confirm: true })
        }
      },
      {
        id: "statusbar",
        area: STATUSBAR_AREAS.right,
        order: 140,
        render: () => /* @__PURE__ */ jsx12(StatusChip, {})
      }
    ]);
  }
};
var index_default = plugin;
export {
  index_default as default
};
