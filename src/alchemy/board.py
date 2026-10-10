"""Match-four rules, independent of the display."""
from random import Random

SIZE = 8
KINDS = 5
PLUS_BONUS = 200


def matched_runs(grid):
    """Return each maximal horizontal or vertical match exactly once."""
    runs = []
    for y in range(SIZE):
        for x in range(SIZE):
            value = grid[y][x]
            if value is None:
                continue
            for dx, dy in ((1, 0), (0, 1)):
                px, py = x - dx, y - dy
                if px >= 0 and py >= 0 and grid[py][px] == value:
                    continue
                run = []
                xx, yy = x, y
                while xx < SIZE and yy < SIZE and grid[yy][xx] == value:
                    run.append((xx, yy))
                    xx += dx
                    yy += dy
                if len(run) >= 4:
                    runs.append(run)
    return runs


def matches(grid):
    return {cell for run in matched_runs(grid) for cell in run}


def shape_crossings(grid):
    """One exclusive L/T/plus classification per crossing of maximal 4+ runs."""
    runs = matched_runs(grid)
    horizontal = [r for r in runs if r[0][1] == r[-1][1]]
    vertical = [r for r in runs if r[0][0] == r[-1][0]]
    shapes = {'l_shape': set(), 't_shape': set(), 'plus': set()}
    for h in horizontal:
        for v in vertical:
            for cell in set(h).intersection(v):
                ends = int(cell in (h[0], h[-1])) + int(cell in (v[0], v[-1]))
                shapes[('plus', 't_shape', 'l_shape')[ends]].add(cell)
    return shapes


def plus_centers(grid):
    """True pluses: both 4+ runs extend on both sides of their crossing."""
    centers = set()
    for y in range(1, SIZE - 1):
        for x in range(1, SIZE - 1):
            value = grid[y][x]
            if value is None:
                continue
            lengths = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                length = 0
                xx, yy = x + dx, y + dy
                while 0 <= xx < SIZE and 0 <= yy < SIZE and grid[yy][xx] == value:
                    length += 1
                    xx, yy = xx + dx, yy + dy
                lengths.append(length)
            right, left, down, up = lengths
            if min(lengths) > 0 and right + left + 1 >= 4 and down + up + 1 >= 4:
                centers.add((x, y))
    return centers


def swap(grid, a, b):
    ax, ay = a
    bx, by = b
    grid[ay][ax], grid[by][bx] = grid[by][bx], grid[ay][ax]


def legal_moves(grid):
    result = []
    for y in range(SIZE):
        for x in range(SIZE):
            for b in ((x + 1, y), (x, y + 1)):
                if b[0] >= SIZE or b[1] >= SIZE:
                    continue
                a = (x, y)
                swap(grid, a, b)
                if matches(grid):
                    result.append((a, b))
                swap(grid, a, b)
    return result


def new_grid(rng):
    while True:
        grid = [[rng.randrange(KINDS) for _ in range(SIZE)] for _ in range(SIZE)]
        if not matches(grid) and legal_moves(grid):
            return grid


def refill(grid, cleared, rng):
    for x in range(SIZE):
        remaining = [grid[y][x] for y in range(SIZE) if (x, y) not in cleared]
        column = [rng.randrange(KINDS) for _ in range(SIZE - len(remaining))] + remaining
        for y, value in enumerate(column):
            grid[y][x] = value


class Game:
    def __init__(self, seed=None):
        self.rng = Random(seed)
        self.grid = new_grid(self.rng)
        self.score = 0
        self.moves = 30
        self.chain = 0
        self.last_reaction = None
        self.hint_index = 0
        self.pending = set()
        self.message = 'Select a symbol, then an adjacent symbol.'

    def attempt(self, a, b):
        if self.pending or self.moves <= 0:
            return False
        if any(not isinstance(v, int) for cell in (a, b) for v in cell):
            return False
        if any(not (0 <= x < SIZE and 0 <= y < SIZE) for x, y in (a, b)):
            return False
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False
        swap(self.grid, a, b)
        self.pending = matches(self.grid)
        if not self.pending:
            swap(self.grid, a, b)
            self.message = 'Make a line of at least four. Try another swap.'
            return False
        self.moves -= 1
        self.chain = 0
        return True

    def hint(self):
        if self.pending or self.moves <= 0:
            return None
        options = legal_moves(self.grid)
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
        count = len(self.pending)
        shapes = shape_crossings(self.grid)
        pluses = len(shapes['plus'])
        l_bonus = len(shapes['l_shape']) * 100
        t_bonus = len(shapes['t_shape']) * 150
        bonus = pluses * PLUS_BONUS
        length_bonus = sum((len(run) - 4) * 25 for run in matched_runs(self.grid))
        points = (count * 25 + length_bonus + bonus + l_bonus + t_bonus) * self.chain
        self.last_reaction = dict(base=count * 25, length=length_bonus, plus=bonus,
                                  multiplier=self.chain, total=points, l_shape=l_bonus, t_shape=t_bonus)
        self.hint_index = 0
        events = ["cascade" if self.chain > 1 else "match"]
        for shape, cells in shapes.items():
            if cells:
                events.append(shape)
        self.score += points
        self.message = f'{count} symbols transmuted!  +{points}  /  Cascade x{self.chain}'
        labels = [label for key, label in (('l_shape', 'L reaction'), ('t_shape', 'T reaction'), ('plus', 'Plus reaction')) if shapes[key]]
        if labels:
            self.message += '  /  ' + ', '.join(labels)
        refill(self.grid, self.pending, self.rng)
        self.pending = matches(self.grid)
        if not self.pending and self.moves and not legal_moves(self.grid):
            self.grid = new_grid(self.rng)
            self.message = 'No swaps left: a fresh board has been brewed.'
            events.append("shuffle")
        if not self.pending and not self.moves:
            events.append("game_over")
        return events
