"""Deck construction and shuffling.

Normal play uses `secure_deck()`, which shuffles with `secrets.SystemRandom`
and cannot be seeded from outside — the deck factory is a constructor
argument on `Table.new`; the service passes `secure_deck` for real games.
Test-only hooks `seeded_deck` and `fixed_deck` produce deterministic decks
for fixtures and simulation tests.
"""
import secrets

from .cards import full_deck


def secure_deck():
    """Return a freshly shuffled 52-card deck using a CSPRNG.

    A new `secrets.SystemRandom` instance shuffles a fresh card list every
    call; there is no seed argument anywhere in this path, so normal play
    can never be reproduced or predicted from outside the process.
    """
    cards = full_deck()
    secrets.SystemRandom().shuffle(cards)
    return cards


def seeded_deck(seed):
    """Test-only: a deterministically shuffled deck from `seed`.

    Uses `random.Random(seed)`, NOT `secrets` — never call this from
    production code paths (only tests/fixtures should import it).
    """
    import random

    cards = full_deck()
    random.Random(seed).shuffle(cards)
    return cards


def fixed_deck(cards):
    """Test-only: a factory returning a predetermined deck order.

    `cards` is the desired order for the top of the deck (dealt first).
    Any of the 52 standard cards missing from `cards` are appended in a
    fixed, deterministic order (full_deck() order, minus those already
    used) so the returned deck always has exactly 52 unique cards.
    """
    cards = list(cards)
    seen = set(cards)
    for c in full_deck():
        if c not in seen:
            cards.append(c)
            seen.add(c)
    if len(cards) != 52 or len(set(cards)) != 52:
        raise ValueError("fixed_deck: invalid or duplicate cards")

    def factory():
        return list(cards)

    return factory
