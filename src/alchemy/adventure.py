"""Finite material experiments; reaction scoring is shared with Classic."""
from collections import Counter
from dataclasses import dataclass

from .board import Game, SIZE, matches, legal_moves
from .modes import ADVENTURE


@dataclass(frozen=True)
class Experiment:
    key: str = 'adventure-first-v2'
    title: str = 'First Transmutation'
    target: int = 3500
    reserves: tuple = (20, 20, 20, 20)
    seed: int = 42
    stir_attempts: int = 200


FIRST_EXPERIMENT = Experiment()


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
        super().__init__(self.seed, ADVENTURE)
        self.reserves = list(experiment.reserves)
        self.outcome = None
        self.failure_reason = None
        self.consumed = 0
        self.turns = 0
        self.stirs = 0
        self.initial_material = SIZE*SIZE + sum(self.reserves)
        self.message = f'{experiment.title}: reach {experiment.target:,} points.'

    @property
    def finished(self):
        return self.outcome is not None

    @property
    def points_remaining(self):
        return max(0, self.experiment.target-self.score)

    @property
    def failure_summary(self):
        if self.failure_reason == 'insufficient_material':
            return 'Too few of each element for another match.'
        return 'Stir could not find a playable arrangement.'

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
        if self.score >= self.experiment.target:
            self.outcome = 'success'
            self.message = 'Experiment complete: target reached!'
        elif not legal_moves(self.grid, self.mode):
            if stir(self.grid, self.rng, self.mode, self.experiment.stir_attempts):
                self.stirs += 1
                self.message = 'Vessel stirred: the same material, rearranged.'
                events.append('shuffle')
            else:
                self.outcome = 'stalled'
                counts = Counter(v for row in self.grid for v in row if v is not None)
                self.failure_reason = ('insufficient_material' if max(counts.values(), default=0) < 4
                                       else 'search_exhausted')
                self.message = f'{self.failure_summary} {self.points_remaining:,} points short.'
        if self.finished:
            events.append('game_over')
