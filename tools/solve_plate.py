"""Solve and generate fixed campaign plates (no reserves, no stirs, a swap limit).

A plate has no refill, so play is deterministic: the solver searches every sequence of
swaps breadth-first, merging identical positions, and reports the fewest swaps that
win and how many distinct winning lines of that length exist.

Run from the checkout:
  uv run python tools/solve_plate.py                 # solve the shipped Red Plate
  uv run python tools/solve_plate.py --generate 300  # search seeds for new plates
"""
import argparse
import copy
from collections import Counter
from dataclasses import replace
from random import Random

from alchemy.adventure import CAMPAIGN_KITS, PURIFY, AdventureGame, Experiment
from alchemy.board import LINE, SIZE, SQUARE, legal_moves, matches


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
    args = parser.parse_args()
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
