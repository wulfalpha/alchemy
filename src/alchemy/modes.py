"""Game variants: which symbols are in play and which directions can match.

A mode is pure data with no pygame or board dependency, so `board.py` stays a
rules module and `app.py` reads its colours and copy from here instead of from
module globals. Scoreboards are partitioned by `Mode.key` (the scoreboard's
MODE column), while `scores.RULES` versions the scoring formula itself.
"""
from dataclasses import dataclass

# Each unordered direction appears once: (-1, 1) covers the anti-diagonal both ways.
ORTHOGONAL = ((1, 0), (0, 1))
DIAGONAL = ((1, 0), (0, 1), (1, 1), (-1, 1))

ELEMENTS = ('fire', 'water', 'air', 'earth')
WITH_SUN = ELEMENTS + ('sun',)
ELEMENT_COLORS = ((107, 54, 45), (38, 80, 103), (73, 89, 77), (85, 68, 104))
SUN_COLOR = (110, 88, 42)

STRAIGHT_PRACTICE = ('Swap two neighboring symbols.',
                     'Align 4 or more in a row or column.',
                     'Cleared symbols make room for new ones.',
                     'Chain reactions multiply your points.',
                     'L +100 / T +150 / Plus +200.')
DIAGONAL_PRACTICE = ('Swap any touching symbols, diagonals too.',
                     'Align 4+ in rows, columns, or diagonals.',
                     'Cleared symbols make room for new ones.',
                     'Chain reactions multiply your points.',
                     'L +100 / T +150 / Plus +200.')


@dataclass(frozen=True)
class Mode:
    """One playable variant. `key` is durable: it identifies saved scores."""
    key: str
    label: str
    caption: str
    tagline: str
    names: tuple
    colors: tuple
    directions: tuple = ORTHOGONAL   # directions a matching line may run in
    swaps: tuple = ORTHOGONAL        # directions a swap may reach
    moves: int = 30
    practice: tuple = STRAIGHT_PRACTICE

    def __post_init__(self):
        if len(self.names) != len(self.colors):
            raise ValueError(f'{self.key}: {len(self.names)} symbols but {len(self.colors)} colours')
        if self.kinds < 2 or self.moves < 1 or not self.directions or not self.swaps:
            raise ValueError(f'{self.key}: needs 2+ symbols, 1+ moves, a match direction, and a swap direction')

    @property
    def kinds(self):
        return len(self.names)


CLASSIC = Mode(
    key='classic-30',
    label='Classic',
    caption='Alchemy | The Fourfold Art',
    tagline='Four elements, straight lines.',
    names=ELEMENTS,
    colors=ELEMENT_COLORS,
)

DIAGONALS = Mode(
    key='diagonal-30',
    label='Diagonal',
    caption='Alchemy | The Diagonal Art',
    tagline='Swap and match in every direction.',
    names=WITH_SUN,
    colors=ELEMENT_COLORS + (SUN_COLOR,),
    directions=DIAGONAL,
    swaps=DIAGONAL,
    practice=DIAGONAL_PRACTICE,
)

MODES = {mode.key: mode for mode in (CLASSIC, DIAGONALS)}
DEFAULT_KEY = CLASSIC.key
DEFAULT_MODE = MODES[DEFAULT_KEY]

# Five-element orthogonal play is retired. Scores recorded under those rules stay
# in the database as mode 'classic-30' with scores.LEGACY_RULES, labelled "legacy" and
# reachable from the scoreboard's Tab view; nothing is rewritten or deleted.
