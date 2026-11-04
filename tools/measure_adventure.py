"""Reproducible medal calibration using random and visible-reaction policies.

Run from the checkout: uv run python tools/measure_adventure.py --runs 60
Each policy/experiment uses the same seed schedule and independent choice RNGs.
The efficient policy considers only the visible first reaction, never future tiles.
"""
import argparse
from collections import Counter
import json
from random import Random
from statistics import median

from alchemy.adventure import AdventureGame, EXPERIMENTS
from alchemy.board import legal_moves, matched_runs, shape_crossings, swap


def choose_move(game, policy, rng):
    moves = legal_moves(game.grid, game.mode)
    if policy == 'random':
        return rng.choice(moves)
    ranked = []
    for move in moves:
        grid = [row[:] for row in game.grid]
        swap(grid, *move)
        runs = matched_runs(grid, game.mode)
        count = len(set().union(*map(set, runs)))
        shapes = shape_crossings(grid, game.mode, runs)
        points = (count * 25 + sum((len(run)-4)*25 for run in runs)
                  + len(shapes['l_shape'])*100 + len(shapes['t_shape'])*150
                  + len(shapes['plus'])*200)
        ranked.append((points / count, points))
    best = max(ranked)
    return rng.choice([move for move, rank in zip(moves, ranked) if rank == best])


def measure(runs, fixed_seed=None):
    reports = []
    for name, experiment in EXPERIMENTS.items():
        for policy in ('random', 'efficient'):
            outcomes = Counter()
            material = []
            for index in range(runs):
                seed = index if fixed_seed is None else fixed_seed
                game = AdventureGame(seed, experiment)
                choices = Random(10000 + index)
                while not game.finished:
                    game.attempt(*choose_move(game, policy, choices))
                    while game.pending:
                        game.resolve()
                outcomes[game.outcome if game.outcome == 'success' else game.failure_reason] += 1
                if game.outcome == 'success':
                    material.append(game.material_left)
            ordered = sorted(material)
            reports.append(dict(mode=name, policy=policy, runs=runs, fixed_seed=fixed_seed,
                                outcomes=dict(outcomes), material_min=min(material, default=None),
                                material_median=median(material) if material else None,
                                material_p75=ordered[int((len(ordered)-1)*.75)] if ordered else None,
                                material_max=max(material, default=None),
                                winners_at_least={str(n): sum(m >= n for m in material)
                                                  for n in (25, 30, 35, 40, 45, 50)}))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=60)
    parser.add_argument('--seed', type=int, help='Use one starting seed instead of seeds 0..runs-1')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    print(json.dumps(measure(args.runs, args.seed), indent=2))


if __name__ == '__main__':
    main()
