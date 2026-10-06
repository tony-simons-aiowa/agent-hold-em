"""Agent Hold 'Em — authoritative No-Limit Texas Hold 'Em engine.

Pure, synchronous, deterministic given a deck. No I/O, no clocks, no threads,
no Hermes imports — stdlib only. See docs/ARCHITECTURE.md §3 for the binding
interface contract and docs/TESTING.md for rule-decision documentation.
"""

from .errors import IllegalAction
from .deck import secure_deck, seeded_deck, fixed_deck
from .cards import RANKS, SUITS, parse_card, card_rank, card_suit
from .evaluator import evaluate_best5, evaluate_seven, hand_label
from .legal import Action, Legal
from .table import Table

__all__ = [
    "IllegalAction",
    "secure_deck",
    "seeded_deck",
    "fixed_deck",
    "RANKS",
    "SUITS",
    "parse_card",
    "card_rank",
    "card_suit",
    "evaluate_best5",
    "evaluate_seven",
    "hand_label",
    "Action",
    "Legal",
    "Table",
]
