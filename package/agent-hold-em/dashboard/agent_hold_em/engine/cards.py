"""Card representation: 2-char strings, rank "23456789TJQKA" + suit "cdhs"."""

RANKS = "23456789TJQKA"
SUITS = "cdhs"

_RANK_TO_INT = {r: i + 2 for i, r in enumerate(RANKS)}  # '2' -> 2 ... 'A' -> 14
_INT_TO_RANK = {v: k for k, v in _RANK_TO_INT.items()}

RANK_NAMES = {
    2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven",
    8: "Eight", 9: "Nine", 10: "Ten", 11: "Jack", 12: "Queen", 13: "King",
    14: "Ace",
}
RANK_NAMES_PLURAL = {
    2: "Twos", 3: "Threes", 4: "Fours", 5: "Fives", 6: "Sixes", 7: "Sevens",
    8: "Eights", 9: "Nines", 10: "Tens", 11: "Jacks", 12: "Queens",
    13: "Kings", 14: "Aces",
}
SUIT_NAMES = {"c": "Clubs", "d": "Diamonds", "h": "Hearts", "s": "Spades"}


def full_deck():
    """A fresh, ordered 52-card list (rank-major, suit-minor)."""
    return [r + s for r in RANKS for s in SUITS]


def parse_card(card: str):
    """Validate and split a card string into (rank_int, suit_char)."""
    if not isinstance(card, str) or len(card) != 2:
        raise ValueError(f"invalid card: {card!r}")
    r, s = card[0], card[1]
    if r not in _RANK_TO_INT or s not in SUITS:
        raise ValueError(f"invalid card: {card!r}")
    return _RANK_TO_INT[r], s


def card_rank(card: str) -> int:
    return _RANK_TO_INT[card[0]]


def card_suit(card: str) -> str:
    return card[1]


def rank_int_to_char(rank: int) -> str:
    return _INT_TO_RANK[rank]
