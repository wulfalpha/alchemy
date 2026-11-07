"""Solve and generate fixed campaign plates (no reserves, no stirs, a swap limit).

A plate has no refill, so play is deterministic: the solver searches every sequence of
swaps breadth-first, merging identical positions, and reports the fewest swaps that
win and how many distinct winning lines of that length exist.

Run from the checkout:
  uv run python tools/solve_plate.py                 # solve the shipped Red Plate
  uv run python tools/solve_plate.py --generate 300  # search seeds for new plates
  uv run python tools/solve_plate.py --finale 300    # search for Philosopher's Plate candidates
  uv run python tools/solve_plate.py --finale 300 --salt 2
"""
import argparse
import copy
from collections import Counter
from dataclasses import replace
from random import Random

from alchemy.adventure import CAMPAIGN_KITS, PURIFY, AdventureGame, Experiment
from alchemy.board import ELEMENT, LINE, SALT, SIZE, SQUARE, legal_moves, matches


# Clear every fire tile from a plate with no reserves.
PLATE_BASE = Experiment(key='adventure-plate-candidate', title='Candidate', reserves=(0, 0, 0, 0),
                        unstable=True, objective=PURIFY, element=0, medal_by='swaps')


def clone(game):
    twin = copy.copy(game)
    twin.grid = [row[:] for row in game.grid]
    twin.unstable = dict(game.unstable)
    twin.reserves = list(game.reserves)
    twin.banked = Counter(game.banked)
    return twin


def play(game, move):
    """The position after a swap and its whole cascade, or None if the swap is refused."""
    twin = clone(game)
    if not twin.attempt(*move):
        return None
    while twin.pending:
        twin.resolve()
    return twin


def position(game):
    return tuple(map(tuple, game.grid)), frozenset(game.unstable.items())


def solve(experiment, limit=None, max_positions=400_000):
    """Return (fewest swaps, winning lines of that length, positions searched).

    Fewest swaps is None when no line wins within `limit` (the plate's swap limit by
    default), or when the search exceeds `max_positions` (then searched is negative).
    """
    limit = experiment.swap_limit if limit is None else limit
    start = AdventureGame(experiment=experiment)
    frontier = {position(start): (start, ())}
    seen = set(frontier)
    for depth in range(1, limit + 1):
        wins, following = [], {}
        for game, line in frontier.values():
            for move in legal_moves(game.grid, game.mode):
                child = play(game, move)
                if child is None:
                    continue
                if child.outcome == 'success':
                    wins.append(line + (move,))
                    continue
                key = position(child)
                if child.finished or key in seen:
                    continue
                seen.add(key)
                following[key] = (child, line + (move,))
                if len(seen) > max_positions:
                    return None, [], -len(seen)
        if wins:
            return depth, wins, len(seen)
        frontier = following
    return None, [], len(seen)


def random_plate(rng, fire=8):
    """A gravity-stable sparse plate with no ready match, `fire` fire tiles, and two
    unstable symbols (a Line and a Square) on non-fire tiles."""
    for _ in range(1000):
        heights = [rng.randint(5, 8) for _ in range(SIZE)]
        cells = [(x, y) for x in range(SIZE) for y in range(SIZE - heights[x], SIZE)]
        if len(cells) < fire + 12:
            continue
        values = [0] * fire + [rng.choice((1, 2, 3)) for _ in range(len(cells) - fire)]
        rng.shuffle(values)
        grid = [[None] * SIZE for _ in range(SIZE)]
        for (x, y), value in zip(cells, values):
            grid[y][x] = value
        if matches(grid):
            continue
        others = [cell for cell in cells if grid[cell[1]][cell[0]] != 0]
        marked = rng.sample(others, 2)
        layout = tuple(''.join('.' if v is None else 'fwae'[v] for v in row) for row in grid)
        return layout, ((marked[0], LINE), (marked[1], SQUARE))
    raise RuntimeError('no plate found')


# The Philosopher's Plate: clear every fire and water tile; water dissolves salt.
FINALE_BASE = replace(PLATE_BASE, key='adventure-plate-finale-candidate', element=(0, 1), dissolver=1)


def random_finale_plate(rng, fire=7, water=(5, 8), salt=0):
    """A gravity-stable plate with no ready match: `fire` fire, a random count of water in
    the `water` range, `salt` salt tiles, an Element symbol on a fire tile, and a Line and
    a Square on other tiles."""
    for _ in range(1000):
        heights = [rng.randint(5, 8) for _ in range(SIZE)]
        cells = [(x, y) for x in range(SIZE) for y in range(SIZE - heights[x], SIZE)]
        wet = rng.randint(*water)
        if len(cells) < fire + wet + salt + 12:
            continue
        values = [0] * fire + [1] * wet + [SALT] * salt
        values += [rng.choice((2, 3)) for _ in range(len(cells) - len(values))]
        rng.shuffle(values)
        grid = [[None] * SIZE for _ in range(SIZE)]
        for (x, y), value in zip(cells, values):
            grid[y][x] = value
        if matches(grid):
            continue
        fires = [cell for cell in cells if grid[cell[1]][cell[0]] == 0]
        others = [cell for cell in cells if grid[cell[1]][cell[0]] in (1, 2, 3)]
        element = rng.choice(fires)
        line, square = rng.sample(others, 2)
        letters = {None: '.', SALT: 's', 0: 'f', 1: 'w', 2: 'a', 3: 'e'}
        layout = tuple(''.join(letters[v] for v in row) for row in grid)
        return layout, ((element, ELEMENT), (line, LINE), (square, SQUARE))
    raise RuntimeError('no plate found')


def generate_finale(count, salt=0, swap_limit=7, start=0):
    """Print finale plates whose best line needs 5-6 swaps and that can't be won without
    the Element symbol."""
    for seed in range(start, start + count):
        layout, marks = random_finale_plate(Random(seed), salt=salt)
        candidate = replace(FINALE_BASE, layout=layout, marks=marks, swap_limit=swap_limit)
        if solve(candidate, limit=4)[0] is not None:
            continue                                  # too easy
        best, lines, searched = solve(candidate, limit=6)
        if best is None:
            continue
        without = replace(candidate, marks=tuple(m for m in marks if m[1] != ELEMENT))
        if solve(without)[0] is not None:
            continue                                  # the Element blast must matter
        print(f'seed {seed}: best {best}, {len(lines)} winning lines, {searched} positions')
        print('  layout=' + repr(layout))
        print('  marks=' + repr(marks), flush=True)


def generate(count, base, swap_limit=6):
    """Print plates whose best line needs 4-5 swaps and is impossible without symbols."""
    for seed in range(count):
        layout, marks = random_plate(Random(seed))
        candidate = replace(base, layout=layout, marks=marks, swap_limit=swap_limit)
        if solve(candidate, limit=3)[0] is not None:
            continue                                  # too easy
        best, lines, searched = solve(candidate)
        if best is None:
            continue
        unaided = solve(replace(candidate, marks=()))[0]
        if unaided is not None:
            continue                                  # the symbols must matter
        print(f'seed {seed}: best {best}, {len(lines)} winning lines, {searched} positions')
        print('  layout=' + repr(layout))
        print('  marks=' + repr(marks), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--generate', type=int, metavar='SEEDS', help='Try this many generator seeds')
    parser.add_argument('--finale', type=int, metavar='SEEDS', help="Try this many Philosopher's Plate seeds")
    parser.add_argument('--salt', type=int, default=0, help='Salt tiles on each finale candidate')
    parser.add_argument('--start', type=int, default=0, help='First finale seed')
    args = parser.parse_args()
    if args.finale:
        generate_finale(args.finale, salt=args.salt, start=args.start)
        return
    plates = [kit.experiment for kit in CAMPAIGN_KITS if kit.experiment.layout]
    if args.generate:
        generate(args.generate, PLATE_BASE)
        return
    for plate in plates:
        best, lines, searched = solve(plate)
        print(f'{plate.title}: best {best} swaps, {len(lines)} winning lines, {searched} positions')
        if lines:
            print('  e.g.', ' '.join(f'{a}-{b}' for a, b in lines[0]))


if __name__ == '__main__':
    main()
