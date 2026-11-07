"""Finite material experiments; reaction scoring is shared with Classic."""
from collections import Counter
from dataclasses import dataclass, replace

from .board import ELEMENT, Game, SIZE, matches, legal_moves
from .modes import ADVENTURE
from .medals import efficiency_medal, V1_THRESHOLDS, UNSTABLE_THRESHOLDS


# Objectives: reach the points target, remove every tile of one element (`element`, an
# index into the mode's names) from board and reserves, or detonate `detonations`
# unstable symbols of any kind.
POINTS, PURIFY, DETONATE = 'points', 'purify', 'detonate'


@dataclass(frozen=True)
class Experiment:
    key: str = 'adventure-first-v2'
    title: str = 'First Transmutation'
    target: int = 3500
    reserves: tuple = (20, 20, 20, 20)
    seed: int = 42
    stir_attempts: int = 200
    stir_limit: int | None = None
    unstable: bool = False   # skilful matches leave unstable symbols (see board.py)
    medals: tuple = V1_THRESHOLDS   # (silver, gold) material left; see medals.py
    objective: str = POINTS
    element: int | None = None      # the element a PURIFY objective removes
    detonations: int = 1            # unstable symbols a DETONATE objective needs
    start_unstable: tuple = ()      # (element, tier) symbols placed on the opening board


# Released definitions stay unchanged so their saved scores keep their meaning.
FIRST_EXPERIMENT = Experiment()
PREVIOUS_EXPERIMENTS = {
    'adventure': FIRST_EXPERIMENT,
    'adventure-3': replace(FIRST_EXPERIMENT, key='adventure-3-v1', stir_limit=3),
    'adventure-5': replace(FIRST_EXPERIMENT, key='adventure-5-v1', stir_limit=5),
    'adventure-8': replace(FIRST_EXPERIMENT, key='adventure-8-v1', stir_limit=8),
}
# Current revisions: the same kits and stir limits, with unstable symbols. They make
# efficient play much stronger, so medal thresholds rise (docs/medal_calibration.md).
_UNSTABLE = dict(unstable=True, medals=UNSTABLE_THRESHOLDS)
EXPERIMENTS = {
    'adventure': replace(FIRST_EXPERIMENT, key='adventure-first-v3', **_UNSTABLE),
    'adventure-3': replace(PREVIOUS_EXPERIMENTS['adventure-3'], key='adventure-3-v2', **_UNSTABLE),
    'adventure-5': replace(PREVIOUS_EXPERIMENTS['adventure-5'], key='adventure-5-v2', **_UNSTABLE),
    'adventure-8': replace(PREVIOUS_EXPERIMENTS['adventure-8'], key='adventure-8-v2', **_UNSTABLE),
}


@dataclass(frozen=True)
class Kit:
    """One stage of the campaign: an authored experiment and the idea it teaches."""
    stage: str
    experiment: Experiment
    lesson: str


# Chapter 1 of the campaign: one stage per phase of the Great Work (Rubedo is planned).
CHAPTER = 'Chapter 1'
CHAPTER_TITLE = 'The Great Work'

# The campaign, in unlock order. Each kit is one fixed design with its own stir limit and
# medal thresholds; numbers are calibrated in docs/design_notes.md. Never change a released
# kit's experiment: give it a new key instead, as for First Transmutation.
CAMPAIGN_KITS = (
    Kit('Nigredo', Experiment(key='adventure-kit-dry-flask-v1', title='The Dry Flask', target=3500,
                              reserves=(20, 8, 20, 20), seed=42, stir_limit=8, unstable=True,
                              medals=(30, 40)),
        'Water is scarce, so spend it wisely.'),
    Kit('Albedo', Experiment(key='adventure-kit-purification-v1', title='Purification', reserves=(20, 20, 20, 12),
                             seed=42, stir_limit=8, unstable=True, medals=(30, 40), objective=PURIFY,
                             element=3, start_unstable=((3, ELEMENT),)),
        'Remove every earth tile. Time the Element blast.'),
    Kit('Citrinitas', Experiment(key='adventure-kit-golden-shape-v1', title='The Golden Shape',
                                 reserves=(12, 12, 12, 12), seed=42, stir_limit=8, unstable=True,
                                 medals=(40, 50), objective=DETONATE, detonations=3),
        'Form and detonate 3 unstable symbols.'),
)
_BY_KEY = {e.key: e for e in (*PREVIOUS_EXPERIMENTS.values(), *EXPERIMENTS.values(),
                              *(kit.experiment for kit in CAMPAIGN_KITS))}


def medal_thresholds(experiment_key):
    """(silver, gold) for a saved experiment revision; unknown and older keys use v1."""
    experiment = _BY_KEY.get(experiment_key)
    return experiment.medals if experiment else V1_THRESHOLDS


def finite_refill(grid, cleared, reserves, rng):
    """Transfer material from reserves to gaps; never generate new material."""
    for x in range(SIZE):
        survivors = [grid[y][x] for y in range(SIZE)
                     if (x,y) not in cleared and grid[y][x] is not None]
        replacements = []
        for _ in range(SIZE-len(survivors)):
            total = sum(reserves)
            if not total:
                break
            ticket = rng.randrange(total)
            for element, count in enumerate(reserves):
                if ticket < count:
                    reserves[element] -= 1
                    replacements.append(element)
                    break
                ticket -= count
        column = [None]*(SIZE-len(survivors)-len(replacements)) + replacements + survivors
        for y, value in enumerate(column):
            grid[y][x] = value


def carry_markers(markers, grid, rng):
    """Re-attach unstable markers after a stir.

    `markers` lists (element, tier) pairs taken before the stir. A stir keeps every
    tile, so each marker moves to a randomly chosen unmarked tile of its element.
    """
    cells = {}
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            if value is not None:
                cells.setdefault(value, []).append((x, y))
    carried = {}
    for element, tier in markers:
        cell = rng.choice([c for c in cells[element] if c not in carried])
        carried[cell] = tier
    return carried


def sparse_layout(tiles, mode=ADVENTURE):
    """Build a stable sparse board around a guaranteed horizontal swap.

    Bounded backtracking fills compact columns above A A A B A. Failure is
    inconclusive; callers must not describe it as proof of impossibility.
    """
    if not 5 <= len(tiles) <= 16:
        return None
    counts = Counter(tiles)
    budget = 5000
    for element in sorted(counts):
        if counts[element] < 4:
            continue
        for other in sorted(counts):
            if other == element:
                continue
            remaining = counts.copy()
            remaining[element] -= 4
            remaining[other] -= 1
            grid = [[None]*SIZE for _ in range(SIZE)]
            grid[-1][:5] = [element, element, element, other, element]
            heights = [1]*5 + [0]*3

            def fill(left):
                nonlocal budget
                budget -= 1
                if budget < 0:
                    return False
                if not left:
                    return bool(legal_moves(grid, mode))
                for value in sorted(remaining, key=lambda v: (-remaining[v], v)):
                    if not remaining[value]:
                        continue
                    for x in sorted(range(SIZE), key=lambda x: (heights[x], x)):
                        if heights[x] == SIZE:
                            continue
                        y = SIZE-1-heights[x]
                        grid[y][x] = value
                        heights[x] += 1
                        remaining[value] -= 1
                        if not matches(grid, mode) and fill(left-1):
                            return True
                        remaining[value] += 1
                        heights[x] -= 1
                        grid[y][x] = None
                return False

            if fill(len(tiles)-5):
                return grid
    return None


def stir(grid, rng, mode=ADVENTURE, attempts=200):
    """Bounded search for a stable playable rearrangement of existing material."""
    tiles = [value for row in grid for value in row if value is not None]
    if not tiles or max(Counter(tiles).values()) < 4:
        return False
    for _ in range(attempts):
        rng.shuffle(tiles)
        # Distribute all tiles over columns, then compact each toward the bottom.
        columns = [[] for _ in range(SIZE)]
        slots = list(range(SIZE*SIZE))
        rng.shuffle(slots)
        for slot, value in zip(slots, tiles):
            columns[slot % SIZE].append(value)
        candidate = [[None]*SIZE for _ in range(SIZE)]
        for x, column in enumerate(columns):
            for y, value in enumerate(column, start=SIZE-len(column)):
                candidate[y][x] = value
        if not matches(candidate, mode) and legal_moves(candidate, mode):
            grid[:] = candidate
            return True
    candidate = sparse_layout(tiles, mode)
    if candidate is not None:
        grid[:] = candidate
        return True
    return False


class AdventureGame(Game):
    def __init__(self, seed=None, experiment=FIRST_EXPERIMENT):
        self.experiment = experiment
        self.seed = experiment.seed if seed is None else seed
        super().__init__(self.seed, replace(ADVENTURE, unstable=experiment.unstable))
        self.reserves = list(experiment.reserves)
        self.outcome = None
        self.failure_reason = None
        self.consumed = 0
        self.turns = 0
        self.stirs = 0
        self.initial_material = SIZE*SIZE + sum(self.reserves)
        if experiment.start_unstable:
            self.unstable = carry_markers(experiment.start_unstable, self.grid, self.rng)
        self.message = f'{experiment.title}: {self.goal}.'

    @property
    def element_name(self):
        return self.mode.names[self.experiment.element]

    @property
    def element_left(self):
        """Tiles of the PURIFY element still in the vessel and its reserve."""
        e = self.experiment.element
        return self.reserves[e] + sum(v == e for row in self.grid for v in row)

    @property
    def goal(self):
        objective = self.experiment.objective
        if objective == PURIFY:
            return f'remove every {self.element_name} tile'
        if objective == DETONATE:
            return f'detonate {self.experiment.detonations} unstable symbols'
        return f'reach {self.experiment.target:,} points'

    @property
    def objective_title(self):
        objective = self.experiment.objective
        if objective == PURIFY:
            return f'Goal: remove all {self.element_name}'
        if objective == DETONATE:
            return f'Goal: detonate {self.experiment.detonations} unstable'
        return f'Target: {self.experiment.target:,} points'

    @property
    def objective_progress(self):
        objective = self.experiment.objective
        if objective == PURIFY:
            return f'{self.element_left} {self.element_name} left, board and reserve'
        if objective == DETONATE:
            done = f'{min(self.detonations, self.experiment.detonations)} of {self.experiment.detonations} detonated'
            return f'{done}; match a symbol to set it off' if self.unstable else \
                f'{done}; form symbols with 5+ in a row'
        return f'{self.points_remaining:,} points to go'

    @property
    def shortfall(self):
        objective = self.experiment.objective
        if objective == PURIFY:
            return f'{self.element_left} {self.element_name} left'
        if objective == DETONATE:
            return f'{self.detonations} of {self.experiment.detonations} detonated'
        return f'{self.points_remaining:,} points short'

    @property
    def objective_met(self):
        objective = self.experiment.objective
        if objective == PURIFY:
            return self.element_left == 0
        if objective == DETONATE:
            return self.detonations >= self.experiment.detonations
        return self.score >= self.experiment.target

    @property
    def finished(self):
        return self.outcome is not None

    @property
    def medal(self):
        return (efficiency_medal(self.material_left, self.experiment.medals)
                if self.outcome == 'success' else None)

    @property
    def points_remaining(self):
        return max(0, self.experiment.target-self.score)

    @property
    def failure_summary(self):
        if self.failure_reason == 'insufficient_material':
            return 'Too few of each element for another match.'
        if self.failure_reason == 'stirs_exhausted':
            return 'No stirs left to rearrange the vessel.'
        return 'Stir could not find a playable arrangement.'

    @property
    def stirs_remaining(self):
        limit = self.experiment.stir_limit
        return None if limit is None else max(0, limit-self.stirs)

    @property
    def material_left(self):
        return sum(self.reserves) + sum(v is not None for row in self.grid for v in row)

    def attempt(self, a, b):
        accepted = super().attempt(a, b)
        if accepted:
            self.turns += 1
        return accepted

    def _refill(self):
        self.consumed += len(self.pending)
        finite_refill(self.grid, self.pending, self.reserves, self.rng)

    def _settle(self, events):
        if self.pending:
            return
        if self.objective_met:
            self.outcome = 'success'
            self.message = 'Experiment complete: target reached!'
            if self.experiment.objective == PURIFY:
                self.message = f'Experiment complete: the vessel is free of {self.element_name}!'
            elif self.experiment.objective == DETONATE:
                self.message = 'Experiment complete: the symbols are spent!'
        elif not legal_moves(self.grid, self.mode):
            markers = [(self.grid[y][x], tier) for (x, y), tier in sorted(self.unstable.items())]
            counts = Counter(v for row in self.grid for v in row if v is not None)
            if max(counts.values(), default=0) < 4:
                self.outcome = 'stalled'
                self.failure_reason = 'insufficient_material'
            elif self.stirs_remaining == 0:
                self.outcome = 'stalled'
                self.failure_reason = 'stirs_exhausted'
            elif stir(self.grid, self.rng, self.mode, self.experiment.stir_attempts):
                self.unstable = carry_markers(markers, self.grid, self.rng)
                self.stirs += 1
                self.message = 'Vessel stirred: the same material, rearranged.'
                events.append('shuffle')
            else:
                self.outcome = 'stalled'
                self.failure_reason = 'search_exhausted'
            if self.outcome == 'stalled':
                self.message = f'{self.failure_summary} {self.shortfall}.'
        if self.finished:
            events.append('game_over')
