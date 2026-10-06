"""Component B — the Hermes opponent controller.

Turns one seat's observation into one validated action via a real, isolated Hermes
`AIAgent` (zero tools, no memory, no context files, no persistence). See
`docs/CONTRACT.md` (## Hermes agent runtime (verified)) for the verified API
surface this module relies on, and `docs/ARCHITECTURE.md` §4 for the spec.

Public surface: `HermesSeatRunner`, `FakeSeatRunner`, `DecisionRequest`,
`DecisionResult`, `SeatAgentConfig`, `models.list_options`/`models.resolve`.
"""

from .types import Action, DecisionRequest, DecisionResult, SeatAgentConfig
from .fake import FakeSeatRunner
from .runner import HermesSeatRunner

__all__ = [
    "Action",
    "DecisionRequest",
    "DecisionResult",
    "SeatAgentConfig",
    "FakeSeatRunner",
    "HermesSeatRunner",
]
