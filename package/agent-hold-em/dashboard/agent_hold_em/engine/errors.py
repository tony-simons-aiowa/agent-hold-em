"""Error types raised by the engine."""


class IllegalAction(Exception):
    """Raised by Table.apply() when a proposed action is not legal.

    State is guaranteed unchanged when this is raised: apply() validates
    fully before mutating anything.
    """

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message

    def __repr__(self):  # pragma: no cover - debugging aid
        return f"IllegalAction({self.code!r}, {self.message!r})"
