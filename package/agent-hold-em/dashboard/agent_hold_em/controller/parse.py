"""Untrusted-model-output parser + validator (ARCHITECTURE.md §4).

Model output is untrusted input (ARCHITECTURE.md §1 rule 2): this module never
raises on malformed input, never trusts a "kind" or "to" without checking it
against the `legal` dict, and never lets `talk` leak a card. Every public
function here is pure (no I/O, no Hermes imports) so it's cheap to fuzz.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from .types import Action

__all__ = [
    "ParseResult",
    "parse_decision",
    "sanitize_talk",
    "extract_first_json_object",
]

_LEGAL_KINDS = frozenset({"fold", "check", "call", "bet", "raise", "all_in"})


@dataclass(frozen=True, slots=True)
class ParseResult:
    action: Optional[Action]
    talk: Optional[str]
    error: Optional[str]  # short, safe-to-show reason when action is None

    @property
    def ok(self) -> bool:
        return self.action is not None


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def extract_first_json_object(text: str) -> Optional[dict[str, Any]]:
    """Tolerantly extract the first top-level `{...}` JSON object from `text`.

    Handles: a fenced ```json ... ``` block, leading/trailing prose around the
    object, and nested braces/braces-in-strings (via a small brace-depth scan
    rather than a greedy regex, which would mis-match on nested objects). Returns
    None (never raises) when no valid JSON object can be found.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    candidates: list[str] = []
    for m in _CODE_FENCE_RE.finditer(text):
        candidates.append(m.group(1))
    candidates.append(text)  # also try the raw text (fence-less replies)

    for candidate in candidates:
        obj = _scan_first_brace_object(candidate)
        if obj is not None:
            return obj
    return None


def _scan_first_brace_object(text: str) -> Optional[dict[str, Any]]:
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    chunk = text[start:i + 1]
                    try:
                        parsed = json.loads(chunk)
                    except (json.JSONDecodeError, ValueError):
                        break  # try the next '{' below
                    if isinstance(parsed, dict):
                        return parsed
                    break
        start = text.find("{", start + 1)
    return None


# ---------------------------------------------------------------------------
# Validation against a Legal-shaped dict
# ---------------------------------------------------------------------------


def _as_int(value: Any) -> Optional[int]:
    """Strict integer coercion: rejects bool, float (even 40.0), str, None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def parse_decision(raw_text: str, legal: dict[str, Any]) -> ParseResult:
    """Parse + validate one model reply against `legal` (ARCHITECTURE.md §3/§4 `Legal` shape).

    Never raises. `legal["current_bet"]"/"to_call"`/etc. are trusted (server-computed); every
    field FROM THE MODEL is treated as hostile and checked before use.
    """
    obj = extract_first_json_object(raw_text)
    if obj is None:
        return ParseResult(None, None, "no JSON object found in reply")

    raw_kind = obj.get("action")
    if not isinstance(raw_kind, str) or raw_kind not in _LEGAL_KINDS:
        return ParseResult(None, None, f"unknown or missing action {raw_kind!r}")

    talk = sanitize_talk(obj.get("talk")) if "talk" in obj else None

    if raw_kind == "fold":
        if not legal.get("can_fold", True):
            return ParseResult(None, talk, "fold is not legal here")
        return ParseResult({"kind": "fold", "to": None}, talk, None)

    if raw_kind == "check":
        if not legal.get("can_check", False):
            return ParseResult(None, talk, "check is not legal here (there is a bet to call)")
        return ParseResult({"kind": "check", "to": None}, talk, None)

    if raw_kind == "call":
        # "call when to_call==0 -> treat as check" (ARCHITECTURE.md §4).
        if int(legal.get("to_call", 0) or 0) == 0:
            return ParseResult({"kind": "check", "to": None}, talk, None)
        if not legal.get("can_call", False):
            return ParseResult(None, talk, "call is not legal here")
        return ParseResult({"kind": "call", "to": None}, talk, None)

    if raw_kind == "all_in":
        stack = int(legal.get("stack", 0) or 0)
        all_in_to = legal.get("all_in_to")
        if stack <= 0 or all_in_to is None:
            return ParseResult(None, talk, "all_in is not legal here (no chips left)")
        return ParseResult({"kind": "all_in", "to": int(all_in_to)}, talk, None)

    # raw_kind in ("bet", "raise"): both map onto legal["raise_kind"], normalized to the kind the
    # engine actually expects — a model saying "bet" when the engine calls it a "raise" (or vice
    # versa, since there's already a bet on the street) is a naming mismatch, not an illegal
    # action, as long as "to" is in range.
    raise_kind = legal.get("raise_kind")
    if raise_kind not in ("bet", "raise"):
        return ParseResult(None, talk, "betting/raising is not legal here")

    to_value = _as_int(obj.get("to"))
    if to_value is None:
        return ParseResult(None, talk, f"{raw_kind} requires an integer \"to\" amount")

    min_to, max_to = legal.get("min_to"), legal.get("max_to")
    if min_to is None or max_to is None:
        return ParseResult(None, talk, "betting/raising is not legal here")
    min_to, max_to = int(min_to), int(max_to)
    if to_value < min_to or to_value > max_to:
        return ParseResult(None, talk, f"\"to\" {to_value} is outside the legal range [{min_to}, {max_to}]")

    return ParseResult({"kind": raise_kind, "to": to_value}, talk, None)


# ---------------------------------------------------------------------------
# Talk sanitizer
# ---------------------------------------------------------------------------

_MAX_TALK_CHARS = 80

# Suit symbols and words.
_SUIT_SYMBOLS = "♠♥♦♣"
_SUIT_WORDS = r"spades?|hearts?|diamonds?|clubs?"
_RANK_WORDS = (
    r"aces?|kings?|queens?|jacks?|tens?|nines?|eights?|sevens?|sixes?|fives?|fours?|threes?|twos?"
)

_CARD_PATTERNS = [
    # Shorthand rank+suit tokens: As, Kc, 10h, Th, 9d, ... (word-boundary both sides).
    re.compile(r"\b(?:10|[2-9tjqka])[shdc]\b", re.IGNORECASE),
    # Suit symbols anywhere.
    re.compile(f"[{_SUIT_SYMBOLS}]"),
    # "ten of hearts", "king of spades", ...
    re.compile(rf"\b(?:{_RANK_WORDS})\s+of\s+(?:{_SUIT_WORDS})\b", re.IGNORECASE),
    # "pocket aces", "pocket kings", ...
    re.compile(r"\bpocket\s+\w+", re.IGNORECASE),
    # Bare suit words ("hearts", "spades") — a poker table talking about suits at all is
    # reasonably treated as a card mention per ARCHITECTURE.md §4 ("be reasonable").
    re.compile(rf"\b(?:{_SUIT_WORDS})\b", re.IGNORECASE),
]

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_talk(raw: Any) -> Optional[str]:
    """Sanitize `talk` per ARCHITECTURE.md §4: strip URLs/newlines/control chars, truncate to
    80 chars, and drop the whole line entirely if it mentions any card (rank+suit tokens, suit
    symbols, "rank of suit", "pocket X", or a bare suit word).
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    for pattern in _CARD_PATTERNS:
        if pattern.search(text):
            return None  # drop entirely, per spec
    text = _URL_RE.sub("", text)
    text = text.replace("\n", " ").replace("\r", " ")
    text = _CONTROL_CHARS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return text[:_MAX_TALK_CHARS]
