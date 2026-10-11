"""Finite material accounting, completion, and sparse-board behavior."""
from collections import Counter
from dataclasses import replace
from random import Random

import pytest

from alchemy.adventure import AdventureGame, FIRST_EXPERIMENT, finite_refill, stir
from alchemy.board import legal_moves, matches
from alchemy.motion import Motion


def inventory(grid):
    return Counter(v for row in grid for v in row if v is not None)


def test_partial_refill_preserves_elements_and_leaves_compacted_gaps():
    grid = [[None]*8 for _ in range(8)]
    grid[7][0] = 2
    reserves = [1, 0, 2, 0]
    finite_refill(grid, set(), reserves, Random(1))
    assert inventory(grid) == Counter({0: 1, 2: 3})
    assert reserves == [0]*4
    assert grid[7][0] == 2
    for x in range(8):
        column = [row[x] for row in grid]
        assert column[:column.count(None)] == [None]*column.count(None)


def test_crossing_charges_shared_tile_once_and_success_beats_exhaustion():
    game = AdventureGame(experiment=replace(FIRST_EXPERIMENT, target=1, reserves=(0,)*4))
    game.grid = [[None]*8 for _ in range(8)]
    for x in range(4):
        game.grid[7][x] = 0
    for y in range(4, 8):
        game.grid[y][0] = 0
    game.pending = matches(game.grid)
    events = game.resolve()
    assert game.consumed == 7
    assert game.score == 275  # seven tiles + L bonus
    assert game.outcome == 'success' and game.material_left == 0
    assert events.count('game_over') == 1
    assert game.resolve() == []
    assert game.hint() is None
    assert not game.attempt((0, 0), (1, 0))


def test_target_waits_for_entire_cascade():
    game = AdventureGame(experiment=replace(FIRST_EXPERIMENT, target=1, reserves=(4, 0, 0, 0)))
    game.grid = [[None]*8 for _ in range(8)]
    for x in range(4):
        game.grid[7][x] = 1
    game.pending = matches(game.grid)
    assert 'game_over' not in game.resolve()
    assert game.pending and not game.finished
    assert 'game_over' in game.resolve()
    assert game.score == 300 and game.consumed == 8 and game.finished


def test_stalled_layout_does_not_mint_material():
    game = AdventureGame(experiment=replace(FIRST_EXPERIMENT, reserves=(0,)*4))
    game.grid = [[None]*8 for _ in range(8)]
    game.grid[7][:4] = [0]*4
    game.pending = matches(game.grid)
    assert 'game_over' in game.resolve()
    assert game.outcome == 'stalled' and game.material_left == 0


def test_stir_preserves_inventory_and_produces_stable_playable_board():
    grid = [[(x+2*y) % 4 for x in range(8)] for y in range(8)]
    original = inventory(grid)
    assert not legal_moves(grid)
    assert stir(grid, Random(42))
    assert inventory(grid) == original
    assert not matches(grid) and legal_moves(grid)


def test_failed_bounded_stir_leaves_board_unchanged():
    grid = [[None]*8 for _ in range(8)]
    grid[7][:4] = [0]*4
    original = [row[:] for row in grid]
    assert not stir(grid, Random(1), attempts=1)
    assert grid == original


def test_empty_cells_cannot_be_swapped_or_hinted():
    game = AdventureGame()
    game.grid[0][0] = None
    assert not game.attempt((0, 0), (1, 0))
    assert all((0, 0) not in move for move in legal_moves(game.grid))
    assert game.turns == 0


@pytest.mark.parametrize('seed', [0, 7, 42])
def test_full_run_conserves_material_and_is_reproducible(seed):
    config = replace(FIRST_EXPERIMENT, target=999999)
    a, b = AdventureGame(seed, config), AdventureGame(seed, config)
    finishes = 0
    while not a.finished:
        move = legal_moves(a.grid)[0]
        assert a.attempt(*move) and b.attempt(*move)
        while a.pending:
            events = a.resolve()
            assert events == b.resolve()
            finishes += events.count('game_over')
            assert a.grid == b.grid and a.reserves == b.reserves
            assert a.material_left + a.consumed == a.initial_material
            assert all(n >= 0 for n in a.reserves)
    assert finishes == 1 and a.score == b.score
    assert a.outcome == 'stalled' and a.moves is None


def test_sparse_fall_tracks_existing_survivors():
    grid = [[None]*8 for _ in range(8)]
    grid[5][0], grid[6][0], grid[7][0] = 0, 1, 2
    motion = Motion()
    motion.fall({(0, 7)}, 0, grid)
    assert motion.offset(0, 6, 0) == (0, -1)
    assert motion.offset(0, 7, 0) == (0, -1)
