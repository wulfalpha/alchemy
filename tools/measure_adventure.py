"""Reproducible medal calibration using random and visible-reaction policies.

Run from the checkout: uv run python tools/measure_adventure.py --runs 60
Each policy/experiment uses the same seed schedule and independent choice RNGs.
The efficient policy considers only the visible first reaction, never future tiles;
with unstable symbols that includes detonations and newly formed symbols.
For campaign objectives it prefers moves that advance the objective, then points per
material: for purify, removing the element (holding a blast of that element's Element
symbol until its reserve is spent); for detonate, detonating and then forming symbols.
Pass --before to measure the released experiment revisions instead of the current ones,
or --campaign to measure the campaign kits.
"""
import argparse
from collections import Counter
import json
from random import Random
from statistics import median

from alchemy.adventure import AdventureGame, CAMPAIGN_KITS, DETONATE, EXPERIMENTS, PREVIOUS_EXPERIMENTS, PURIFY
from alchemy.board import (ELEMENT, UNSTABLE_POINTS, detonate, legal_moves, matched_runs, shape_crossings, swap,
                           unstable_births)


def first_reaction(game, move, detail=False):
    """Points and material spent by the visible first reaction of a swap.

    With detail, also the purify-element tiles removed, the unstable symbols detonated
    and formed, and whether an Element symbol of the purify element detonates."""
    grid = [row[:] for row in game.grid]
    swap(grid, *move)
    unstable = dict(game.unstable)
    a, b = move
    unstable = {(b if cell == a else a if cell == b else cell): tier for cell, tier in unstable.items()}
    runs = matched_runs(grid, game.mode)
    matched = set().union(*map(set, runs))
    shapes = shape_crossings(grid, game.mode, runs)
    blasted, detonated = detonate(grid, runs, unstable) if unstable else (set(), {})
    blasted -= matched
    births = unstable_births(runs, shapes, move) if game.mode.unstable else {}
    points = (len(matched) * 25 + sum((len(run)-4)*25 for run in runs)
              + len(shapes['l_shape'])*100 + len(shapes['t_shape'])*150
              + len(shapes['plus'])*200 + len(blasted) * UNSTABLE_POINTS)
    spent = len(matched) + len(blasted) - len(births)
    if not detail:
        return points, spent
    element = game.experiment.element
    removed = sum(grid[y][x] == element for x, y in (matched | blasted) - births.keys())
    element_blast = any(tier == ELEMENT and grid[y][x] == element for (x, y), tier in detonated.items())
    return points, spent, removed, len(detonated), len(births), element_blast


def choose_move(game, policy, rng):
    moves = legal_moves(game.grid, game.mode)
    if policy == 'random':
        return rng.choice(moves)
    ranked = []
    objective = game.experiment.objective
    for move in moves:
        points, spent, removed, detonates, forms, element_blast = first_reaction(game, move, detail=True)
        rank = (points / max(spent, 1), points)
        if objective == PURIFY:
            early = element_blast and game.reserves[game.experiment.element] > 0
            rank = (not early, removed / max(spent, 1)) + rank
        elif objective == DETONATE:
            rank = (detonates, forms) + rank
        ranked.append(rank)
    best = max(ranked)
    return rng.choice([move for move, rank in zip(moves, ranked) if rank == best])


def measure(runs, fixed_seed=None, experiments=EXPERIMENTS):
    reports = []
    for name, experiment in experiments.items():
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
            reports.append(dict(mode=name, experiment=experiment.key, policy=policy, runs=runs, fixed_seed=fixed_seed,
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
    parser.add_argument('--before', action='store_true',
                        help='Measure the released revisions (no unstable symbols)')
    parser.add_argument('--campaign', action='store_true', help='Measure the campaign kits')
    args = parser.parse_args()
    if args.runs < 1:
        parser.error('--runs must be positive')
    experiments = PREVIOUS_EXPERIMENTS if args.before else EXPERIMENTS
    if args.campaign:
        experiments = {kit.experiment.title: kit.experiment for kit in CAMPAIGN_KITS}
    print(json.dumps(measure(args.runs, args.seed, experiments), indent=2))


if __name__ == '__main__':
    main()
