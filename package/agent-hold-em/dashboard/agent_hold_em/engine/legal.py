"""Action / Legal value objects (engine interface, ARCHITECTURE.md §3)."""
from dataclasses import dataclass, asdict
from typing import Optional, Literal


ActionKind = Literal["fold", "check", "call", "bet", "raise", "all_in"]


@dataclass(frozen=True)
class Action:
    """A proposed player action.

    `to` is REQUIRED for bet/raise (total street commitment after the
    action — "raise TO" semantics) and must be None for every other kind.

    `fallback` is a documented additive extension beyond the original
    ARCHITECTURE.md §3 sketch (which had only kind/to): it lets the
    service layer's forced check-else-fold fallback (hard rule #8) be
    echoed verbatim into the engine's public `action` event / seat
    `last_action` view field, instead of requiring a parallel side
    channel the engine knows nothing about. Defaults to False and never
    affects legality — purely descriptive metadata carried through.
    """
    kind: str
    to: Optional[int] = None
    fallback: bool = False

    def to_dict(self):
        return {"kind": self.kind, "to": self.to, "fallback": self.fallback}

    @staticmethod
    def from_dict(d):
        return Action(kind=d["kind"], to=d.get("to"), fallback=bool(d.get("fallback", False)))


@dataclass(frozen=True)
class Legal:
    """Exact legal-action bounds for the seat currently to act."""
    seat: int
    to_call: int
    can_fold: bool
    can_check: bool
    can_call: bool
    call_amount: int
    raise_kind: Optional[str]   # "bet" | "raise" | None
    min_to: Optional[int]
    max_to: Optional[int]
    all_in_to: int
    stack: int
    current_bet: int
    committed: int

    def to_dict(self):
        return asdict(self)
