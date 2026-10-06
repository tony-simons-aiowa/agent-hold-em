"""Agent Hold 'Em — Hermes Desktop plugin backend package.

Kept trivial on purpose: no imports at package-import time other than the standard
library, so `import agent_hold_em` never triggers Hermes agent-runtime imports (which
require `scripts/env.sh`'s HERMES_DISABLE_LAZY_INSTALLS=1 to be safe). Submodules
(`agent_hold_em.controller`, `agent_hold_em.engine`, ...) import Hermes lazily,
inside functions, for the same reason.
"""

__all__: list[str] = []
