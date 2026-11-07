"""Match-four rules, independent of the display.

Every rule takes an optional `mode` (see `modes.py`) that supplies the symbol
count and the directions a line may run in. It defaults to the primary mode, so
`matches(grid)` and `Game()` keep working unchanged.
"""
from collections import Counter
from random import Random
from .modes import DEFAULT_MODE, ORTHOGONAL

SIZE = 8
PLUS_BONUS = 200
# Unstable symbols (modes with `unstable=True`): skilful matches leave one behind,
# and a later match that includes it detonates it. See docs/design_notes.md.
LINE, SQUARE, ELEMENT = 'line', 'square', 'element'
UNSTABLE_TIERS = (LINE, SQUARE, ELEMENT)
UNSTABLE_POINTS = 50   # per tile cleared by a detonation, before the cascade multiplier
# Paid once when the game ends for each unstable symbol never detonated: those still on
# the board plus those banked when a dead board was replaced. Kept below what a typical
# detonation earns, so using a symbol is always the better play.
UNUSED_BONUS = {LINE: 100, SQUARE: 150, ELEMENT: 200}


def matched_runs(grid, mode=None):
    """Return each maximal match exactly once, in the mode's directions."""
    directions = (mode or DEFAULT_MODE).directions
    runs = []
    for y in range(SIZE):
        for x in range(SIZE):
            value = grid[y][x]
            if value is None:
                continue
            for dx, dy in directions:
                px, py = x - dx, y - dy
                if 0 <= px < SIZE and 0 <= py < SIZE and grid[py][px] == value:
                    continue
                run = []
                xx, yy = x, y
                while 0 <= xx < SIZE and 0 <= yy < SIZE and grid[yy][xx] == value:
                    run.append((xx, yy))
                    xx += dx
                    yy += dy
                if len(run) >= 4:
                    runs.append(run)
    return runs


def matches(grid, mode=None):
    return {cell for run in matched_runs(grid, mode) for cell in run}


def shape_crossings(grid, mode=None, runs=None):
    """One exclusive L/T/plus classification per crossing of maximal 4+ runs.

    Only horizontal and vertical runs form shapes; a diagonal run earns its
    length bonus but never an L, T, or plus. Pass `runs` to reuse matched_runs().
    """
    runs = matched_runs(grid, mode) if runs is None else runs
    horizontal = [r for r in runs if r[0][1] == r[-1][1]]
    vertical = [r for r in runs if r[0][0] == r[-1][0]]
    shapes = {'l_shape': set(), 't_shape': set(), 'plus': set()}
    for h in horizontal:
        for v in vertical:
            for cell in set(h).intersection(v):
                ends = int(cell in (h[0], h[-1])) + int(cell in (v[0], v[-1]))
                shapes[('plus', 't_shape', 'l_shape')[ends]].add(cell)
    return shapes


def run_direction(run):
    return (run[1][0] - run[0][0], run[1][1] - run[0][1])


def blast_cells(grid, cell, tier, directions=ORTHOGONAL):
    """Occupied cells one unstable symbol clears when it detonates (itself included).

    Line: the whole board line through it in each direction given. Square: the
    3x3 block around it. Element: every symbol on the board of its own element.
    """
    x, y = cell
    if tier == ELEMENT:
        value = grid[y][x]
        return {(cx, cy) for cy in range(SIZE) for cx in range(SIZE) if grid[cy][cx] == value}
    if tier == SQUARE:
        cells = {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    else:
        cells = {cell}
        for dx, dy in directions:
            for sign in (1, -1):
                cx, cy = x + sign*dx, y + sign*dy
                while 0 <= cx < SIZE and 0 <= cy < SIZE:
                    cells.add((cx, cy))
                    cx, cy = cx + sign*dx, cy + sign*dy
    return {(cx, cy) for cx, cy in cells
            if 0 <= cx < SIZE and 0 <= cy < SIZE and grid[cy][cx] is not None}


def detonate(grid, runs, unstable):
    """Everything a reaction clears: the matched runs plus every blast they set off.

    A Line symbol in a matched run clears along that run's direction (both lines
    if it sits on a crossing). Unstable symbols caught in a blast detonate too;
    a Line set off that way clears its row and column. Returns
    `(cleared, detonated)`, where `detonated` maps each symbol that went off to its tier.
    """
    cleared = {cell for run in runs for cell in run}
    directions = {}
    for run in runs:
        for cell in run:
            directions.setdefault(cell, set()).add(run_direction(run))
    queue = sorted(cell for cell in cleared if cell in unstable)
    detonated = {}
    while queue:
        cell = queue.pop()
        if cell in detonated:
            continue
        detonated[cell] = unstable[cell]
        for hit in blast_cells(grid, cell, unstable[cell], directions.get(cell, ORTHOGONAL)):
            if hit not in cleared:
                cleared.add(hit)
                if hit in unstable:
                    queue.append(hit)
    return cleared, detonated


def unstable_births(runs, shapes, swapped=()):
    """Which cleared cells become unstable symbols, as `{cell: tier}`.

    Rarer patterns earn stronger symbols: any L, T, or plus crossing earns
    Element; a run of 6+ earns Square; a run of exactly 5 earns Line. A run that
    is part of a shape earns nothing more. Each symbol forms on a swapped cell
    when it belongs to the pattern, else on the crossing or the middle of the run.
    """
    births, used = {}, set()
    for kind in ('plus', 't_shape', 'l_shape'):
        for crossing in sorted(shapes[kind]):
            members = set()
            for index, run in enumerate(runs):
                if crossing in run:
                    used.add(index)
                    members.update(run)
            spot = next((c for c in (*(c for c in swapped if c in members), crossing)
                         if c not in births), None)
            if spot is not None:
                births[spot] = ELEMENT
    for index, run in enumerate(runs):
        if index in used or len(run) < 5:
            continue
        candidates = (*(c for c in swapped if c in run), run[len(run)//2], *run)
        spot = next((c for c in candidates if c not in births), None)
        if spot is not None:
            births[spot] = LINE if len(run) == 5 else SQUARE
    return births


def fall_positions(grid, cleared):
    """Where each surviving symbol lands once `cleared` is removed and columns settle."""
    positions = {}
    for x in range(SIZE):
        survivors = [y for y in range(SIZE) if (x, y) not in cleared and grid[y][x] is not None]
        for target, y in enumerate(survivors, start=SIZE - len(survivors)):
            positions[x, y] = (x, target)
    return positions


def adjacent(a, b, mode=None):
    """Whether a and b are one swap apart in this mode (diagonals included if allowed)."""
    offset = (b[0] - a[0], b[1] - a[1])
    opposite = (-offset[0], -offset[1])
    swaps = (mode or DEFAULT_MODE).swaps
    return offset in swaps or opposite in swaps


def swap(grid, a, b):
    ax, ay = a
    bx, by = b
    grid[ay][ax], grid[by][bx] = grid[by][bx], grid[ay][ax]


def legal_moves(grid, mode=None):
    swaps = (mode or DEFAULT_MODE).swaps
    result = []
    for y in range(SIZE):
        for x in range(SIZE):
            for dx, dy in swaps:
                b = (x + dx, y + dy)
                if not (0 <= b[0] < SIZE and 0 <= b[1] < SIZE):
                    continue
                a = (x, y)
                if grid[y][x] is None or grid[b[1]][b[0]] is None:
                    continue
                swap(grid, a, b)
                if matches(grid, mode):
                    result.append((a, b))
                swap(grid, a, b)
    return result


def new_grid(rng, mode=None):
    mode = mode or DEFAULT_MODE
    while True:
        grid = [[rng.randrange(mode.kinds) for _ in range(SIZE)] for _ in range(SIZE)]
        if not matches(grid, mode) and legal_moves(grid, mode):
            return grid


def refill(grid, cleared, rng, mode=None):
    kinds = (mode or DEFAULT_MODE).kinds
    for x in range(SIZE):
        remaining = [grid[y][x] for y in range(SIZE) if (x, y) not in cleared]
        column = [rng.randrange(kinds) for _ in range(SIZE - len(remaining))] + remaining
        for y, value in enumerate(column):
            grid[y][x] = value


class Game:
    def __init__(self, seed=None, mode=None):
        self.mode = mode or DEFAULT_MODE
        self.rng = Random(seed)
        self.grid = new_grid(self.rng, self.mode)
        self.score = 0
        self.moves = self.mode.moves
        self.chain = 0
        self.last_reaction = None
        self.hint_index = 0
        self.pending = set()
        self.unstable = {}         # cell -> tier; empty unless the mode enables them
        self.last_swap = ()
        self.last_cleared = set()  # cells the latest reaction removed (new unstable symbols stay)
        self.banked = Counter()    # tier -> unstable symbols lost when a dead board was replaced
        self.detonations = 0       # unstable symbols detonated so far
        self.unused_bonus = None   # set when the game ends: see cash_in()
        self.message = 'Select a symbol, then an adjacent symbol.'

    @property
    def finished(self):
        return self.moves is not None and self.moves <= 0 and not self.pending

    def attempt(self, a, b):
        if self.pending or self.finished:
            return False
        if any(not isinstance(v, int) for cell in (a, b) for v in cell):
            return False
        if any(not (0 <= x < SIZE and 0 <= y < SIZE) for x, y in (a, b)):
            return False
        if self.grid[a[1]][a[0]] is None or self.grid[b[1]][b[0]] is None:
            return False
        if not adjacent(a, b, self.mode):
            return False
        self._swap(a, b)
        self.pending = self._reaction_cells()
        if not self.pending:
            self._swap(a, b)
            self.message = 'Make a line of at least four. Try another swap.'
            return False
        if self.moves is not None:
            self.moves -= 1
        self.chain = 0
        self.last_swap = (a, b)
        return True

    def _swap(self, a, b):
        swap(self.grid, a, b)
        moved = {cell: self.unstable.pop(cell) for cell in (a, b) if cell in self.unstable}
        for cell, tier in moved.items():
            self.unstable[b if cell == a else a] = tier

    def _reaction_cells(self):
        """The cells the next reaction will clear, blasts included, so the board can show them."""
        runs = matched_runs(self.grid, self.mode)
        return detonate(self.grid, runs, self.unstable)[0] if self.unstable else \
            {cell for run in runs for cell in run}

    def hint(self):
        if self.pending or self.finished:
            return None
        options = legal_moves(self.grid, self.mode)
        if not options:
            self.message = 'No available swaps.'
            return None
        result = options[self.hint_index % len(options)]
        self.hint_index += 1
        return result

    def resolve(self):
        if not self.pending:
            return []
        self.chain += 1
        runs = matched_runs(self.grid, self.mode)
        shapes = shape_crossings(self.grid, self.mode, runs)
        matched = {cell for run in runs for cell in run}
        blasted, detonated = detonate(self.grid, runs, self.unstable)
        blasted -= matched
        self.detonations += len(detonated)
        cleared = self.pending | blasted
        births = (unstable_births(runs, shapes, self.last_swap if self.chain == 1 else ())
                  if self.mode.unstable else {})
        count = len(cleared - blasted)
        pluses = len(shapes['plus'])
        l_bonus = len(shapes['l_shape']) * 100
        t_bonus = len(shapes['t_shape']) * 150
        bonus = pluses * PLUS_BONUS
        length_bonus = sum((len(run) - 4) * 25 for run in runs)
        blast = len(blasted) * UNSTABLE_POINTS
        points = (count * 25 + length_bonus + bonus + l_bonus + t_bonus + blast) * self.chain
        self.last_reaction = dict(base=count * 25, length=length_bonus, plus=bonus,
                                  multiplier=self.chain, total=points, l_shape=l_bonus, t_shape=t_bonus,
                                  unstable=blast)
        self.hint_index = 0
        events = ["cascade" if self.chain > 1 else "match"]
        for shape, cells in shapes.items():
            if cells:
                events.append(shape)
        tiers = [tier for tier in UNSTABLE_TIERS if tier in detonated.values()]
        events += [f'{tier}_burst' for tier in tiers]
        if births:
            events.append('unstable')
        self.score += points
        self.message = f'{len(cleared)} symbols transmuted!  +{points}  /  Cascade x{self.chain}'
        labels = [label for key, label in (('l_shape', 'L reaction'), ('t_shape', 'T reaction'), ('plus', 'Plus reaction')) if shapes[key]]
        labels += [f'{tier.title()} burst' for tier in tiers]
        if births:
            labels.append('Unstable symbol formed' if len(births) == 1 else f'{len(births)} unstable symbols formed')
        if labels:
            self.message += '  /  ' + ', '.join(labels)
        # New unstable symbols take the place of a cleared cell instead of being refilled.
        survivors = {cell: tier for cell, tier in self.unstable.items() if cell not in cleared}
        survivors.update(births)
        self.pending = cleared - births.keys()
        landing = fall_positions(self.grid, self.pending)
        self._refill()
        self.last_cleared = self.pending
        self.unstable = {landing[cell]: tier for cell, tier in survivors.items()}
        self.pending = self._reaction_cells()
        self._settle(events)
        return events

    def _refill(self):
        refill(self.grid, self.pending, self.rng, self.mode)

    def _settle(self, events):
        if not self.pending and self.moves and not legal_moves(self.grid, self.mode):
            self.grid = new_grid(self.rng, self.mode)
            self.message = 'No swaps left: a fresh board has been brewed.'
            if self.unstable:
                lost = len(self.unstable)
                value = sum(UNUSED_BONUS[tier] for tier in self.unstable.values())
                symbols = 'unstable symbol' if lost == 1 else 'unstable symbols'
                self.message = f'No swaps left: fresh board.  {lost} {symbols} banked (+{value}).'
            self.banked.update(self.unstable.values())
            self.unstable = {}
            events.append("shuffle")
        if not self.pending and not self.moves:
            self.cash_in()
            events.append("game_over")

    @property
    def banked_value(self):
        return sum(UNUSED_BONUS[tier] * count for tier, count in self.banked.items())

    def cash_in(self):
        """Pay the unused-symbol bonus once, for symbols left on the board and in the bank."""
        if self.unused_bonus is not None or not self.mode.unstable:
            return
        on_board = Counter(self.unstable.values())
        total = self.banked_value + sum(UNUSED_BONUS[tier] * count for tier, count in on_board.items())
        self.unused_bonus = dict(on_board=sum(on_board.values()), banked=sum(self.banked.values()),
                                 total=total)
        self.score += total
