"""Mode registry: the rules each variant promises, and their isolation from each other.

Consolidates the intent of the two experiment branches (experiment/four-elements and
experiment/diagonal-matches) now that both are mode definitions rather than forks.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from alchemy.board import (Game, SIZE, adjacent, legal_moves, matched_runs, matches,
                           shape_crossings, swap)
from alchemy.modes import CLASSIC, DEFAULT_KEY, DIAGONAL, DIAGONALS, MODES, ORTHOGONAL, Mode
from alchemy.scores import Scoreboard

REPO = Path(__file__).resolve().parents[1]


def dead_grid(mode):
    """Match-free and with no legal swap, in every mode."""
    return [[(x + 2 * y) % mode.kinds for x in range(SIZE)] for y in range(SIZE)]


# ---------- registry ----------

def test_registry_is_keyed_consistently_and_defaults_to_classic():
    assert all(key == mode.key for key, mode in MODES.items())
    assert DEFAULT_KEY == CLASSIC.key == 'classic-30'
    assert set(MODES) == {'classic-30', 'diagonal-30'}  # five-element play is retired


@pytest.mark.parametrize('key', sorted(MODES))
def test_every_mode_is_internally_consistent(key):
    mode = MODES[key]
    assert mode.kinds == len(mode.names) == len(mode.colors) >= 2
    assert mode.moves >= 1 and mode.directions and mode.swaps
    assert len(mode.practice) == 5  # the panel renders exactly five rule lines


def test_mismatched_symbols_and_colours_are_rejected():
    with pytest.raises(ValueError):
        Mode(key='bad', label='Bad', caption='c', tagline='t',
             names=('fire', 'water'), colors=((0, 0, 0),))


# ---------- four elements (was experiment/four-elements) ----------

def test_classic_plays_a_complete_game_with_only_four_elements():
    assert CLASSIC.kinds == 4
    assert CLASSIC.names == ('fire', 'water', 'air', 'earth')
    assert CLASSIC.directions == CLASSIC.swaps == ORTHOGONAL
    game = Game(42, CLASSIC)
    while game.moves:
        assert {v for row in game.grid for v in row} <= {0, 1, 2, 3}
        assert game.attempt(*legal_moves(game.grid, CLASSIC)[0])
        while game.pending:
            game.resolve()
            assert {v for row in game.grid for v in row} <= {0, 1, 2, 3}


@pytest.mark.parametrize('key', sorted(MODES))
def test_grid_values_always_index_into_the_palette(key):
    """The renderer indexes mode.colors[value] directly, with no clamp."""
    mode = MODES[key]
    game = Game(11, mode)
    for _ in range(5):
        assert all(0 <= v < len(mode.colors) for row in game.grid for v in row)
        moves = legal_moves(game.grid, mode)
        if not moves:
            break
        game.attempt(*moves[0])
        while game.pending:
            game.resolve()


# ---------- diagonals (was experiment/diagonal-matches) ----------

@pytest.mark.parametrize('length', [4, 5, 8])
@pytest.mark.parametrize('reverse', [False, True])
def test_diagonal_boundaries_and_long_line_scoring(length, reverse):
    game = Game(1, DIAGONALS)
    game.grid = [[(x + 2 * y) % 5 for x in range(SIZE)] for y in range(SIZE)]
    cells = {(7 - y if reverse else y, y) for y in range(length)}
    for x, y in cells:
        game.grid[y][x] = 9
    assert matches(game.grid, DIAGONALS) == cells
    assert len(matched_runs(game.grid, DIAGONALS)) == 1
    assert not any(shape_crossings(game.grid, DIAGONALS).values())  # diagonals form no shapes
    game.pending = cells
    game.resolve()
    assert game.score == length * 25 + (length - 4) * 25


def test_diagonal_mode_swaps_diagonally_and_classic_does_not():
    assert DIAGONALS.swaps == DIAGONAL
    for neighbour in ((4, 3), (3, 4), (4, 4), (2, 4), (2, 2), (4, 2)):
        assert adjacent((3, 3), neighbour, DIAGONALS), neighbour
    for diagonal in ((4, 4), (2, 4), (2, 2), (4, 2)):
        assert not adjacent((3, 3), diagonal, CLASSIC), diagonal
    for far in ((5, 5), (3, 3), (3, 5)):
        assert not adjacent((3, 3), far, DIAGONALS), far


def test_classic_rejects_a_diagonal_swap_without_spending_a_move():
    game = Game(1, CLASSIC)
    original = [row[:] for row in game.grid]
    assert not game.attempt((0, 0), (1, 1))
    assert game.grid == original and game.moves == CLASSIC.moves


def test_diagonal_mode_accepts_a_diagonal_swap_that_makes_a_line():
    """A swap reachable only diagonally must clear and spend exactly one move."""
    game = Game(1, DIAGONALS)
    game.grid = [[(x + 2 * y) % 5 for x in range(SIZE)] for y in range(SIZE)]
    for y in range(1, 4):
        game.grid[y][y] = 9          # partial diagonal at (1,1) (2,2) (3,3)
    game.grid[4][4] = 0
    game.grid[5][4] = 9              # the fourth symbol, one diagonal step away
    assert not matches(game.grid, DIAGONALS)
    assert game.attempt((4, 5), (4, 4))
    assert game.pending == {(1, 1), (2, 2), (3, 3), (4, 4)}
    assert game.moves == DIAGONALS.moves - 1


@pytest.mark.parametrize('key', sorted(MODES))
def test_every_legal_move_is_adjacent_and_really_matches(key):
    mode = MODES[key]
    game = Game(8, mode)
    moves = legal_moves(game.grid, mode)
    assert moves
    assert all(adjacent(a, b, mode) for a, b in moves)
    assert len({frozenset((a, b)) for a, b in moves}) == len(moves)  # each pair once
    for a, b in moves:
        swap(game.grid, a, b)
        assert matches(game.grid, mode), (a, b)
        swap(game.grid, a, b)


def test_classic_ignores_a_diagonal_that_diagonal_mode_clears():
    grid = [[(x + 2 * y) % 5 for x in range(SIZE)] for y in range(SIZE)]
    for i in range(5):
        grid[i][i] = 9
    assert matches(grid, CLASSIC) == set()
    assert matches(grid, DIAGONALS) == {(i, i) for i in range(5)}


def test_diagonal_mode_still_scores_shapes_on_straight_crossings():
    """Diagonal matching must not cost the L/T/plus bonuses on horizontal/vertical runs."""
    game = Game(2, DIAGONALS)
    game.grid = [[(x + 2 * y) % 5 for x in range(SIZE)] for y in range(SIZE)]
    for x in range(4):
        game.grid[0][x] = 9
    for y in range(4):
        game.grid[y][0] = 9
    assert shape_crossings(game.grid, DIAGONALS)['l_shape'] == {(0, 0)}


# ---------- isolation ----------

@pytest.mark.parametrize('key', sorted(MODES))
def test_dead_board_pattern_is_dead_in_every_mode(key):
    mode = MODES[key]
    grid = dead_grid(mode)
    assert not matches(grid, mode) and legal_moves(grid, mode) == []


def test_modes_rank_separately_on_the_scoreboard(tmp_path):
    board = Scoreboard(tmp_path)
    board.record('a', 'Ada', 500, seed=7, mode=CLASSIC.key)
    board.record('b', 'Bob', 900, seed=7, mode=DIAGONALS.key)
    assert [r['score'] for r in board.top(7, mode=CLASSIC.key)] == [500]
    assert [r['score'] for r in board.top(7, mode=DIAGONALS.key)] == [900]
    board.close()


def test_retired_five_element_scores_are_kept_and_labelled_legacy(tmp_path):
    """Scores from five-element play stay readable under the legacy rules key."""
    from alchemy.scores import LEGACY_RULES, RULES, RULE_HISTORY, RULE_LABELS
    board = Scoreboard(tmp_path)
    board.record('old', 'Ada', 4200, seed=7, mode=CLASSIC.key, rules=LEGACY_RULES)
    board.record('new', 'Bob', 5100, seed=7, mode=CLASSIC.key)
    assert [r['score'] for r in board.top(7, mode=CLASSIC.key)] == [5100]
    assert [r['score'] for r in board.top(7, mode=CLASSIC.key, rules=LEGACY_RULES)] == [4200]
    assert RULE_HISTORY[0] == RULES and LEGACY_RULES in RULE_HISTORY
    assert all(key in RULE_LABELS for key in RULE_HISTORY)
    assert 'Legacy' in RULE_LABELS[LEGACY_RULES]
    board.close()


@pytest.mark.parametrize('key', sorted(MODES))
def test_every_mode_renders_a_frame(key, tmp_path):
    """Catches palette and layout errors that only appear once a mode is drawn."""
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
               PYTHONPATH=str(REPO / 'src'))
    shot = tmp_path / f'{key}.png'
    result = subprocess.run(
        [sys.executable, '-m', 'alchemy', '--smoke-test', '--seed', '42',
         '--mode', key, '--screenshot', str(shot)],
        capture_output=True, text=True, env=env, timeout=60, stdin=subprocess.DEVNULL)
    assert result.returncode == 0, result.stderr
    assert 'Traceback' not in result.stderr
    assert shot.stat().st_size > 0
