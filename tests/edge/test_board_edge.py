"""Edge-case tests for alchemy.board (the pure rules layer).

Tests whose docstring says "Documents" pin current, debatable behaviour (see improvements.md);
update them if that behaviour is changed on purpose.
"""
import random
import time
from random import Random

import pytest

from alchemy import board
from alchemy.board import (Game, SIZE, KINDS, PLUS_BONUS, legal_moves, matches,
                           new_grid, plus_centers, refill, swap)


def checker():
    """A grid with no matches and no 4-runs anywhere."""
    return [[(x + 2 * y) % 5 for x in range(SIZE)] for y in range(SIZE)]


def play_out(game, chooser):
    """Play a whole game; return list of resolve() event lists."""
    log = []
    while game.moves:
        moves = legal_moves(game.grid)
        assert moves, 'invariant broken: no legal moves while moves remain'
        assert game.attempt(*chooser(moves))
        for _ in range(500):
            if not game.pending:
                break
            log.append(game.resolve())
        assert not game.pending
    return log


# ---------- matches() ----------

def test_empty_grid_of_none_has_no_matches():
    assert matches([[None] * SIZE for _ in range(SIZE)]) == set()


def test_uniform_grid_matches_everything():
    assert len(matches([[0] * SIZE for _ in range(SIZE)])) == SIZE * SIZE


def test_run_of_exactly_four_at_far_edges():
    g = checker()
    for x in range(SIZE - 4, SIZE):
        g[SIZE - 1][x] = 9
    assert matches(g) == {(x, SIZE - 1) for x in range(SIZE - 4, SIZE)}
    g = checker()
    for y in range(SIZE - 4, SIZE):
        g[y][SIZE - 1] = 9
    assert matches(g) == {(SIZE - 1, y) for y in range(SIZE - 4, SIZE)}


def test_diagonal_does_not_match():
    g = checker()
    for i in range(5):
        g[i][i] = 9
    assert matches(g) == set()


def test_none_breaks_runs():
    g = checker()
    g[0][:4] = [1, 1, None, 1]
    assert matches(g) == set()


def test_non_int_symbols_work_unicode():
    g = [['🜂🜄🜁🜃☉'[(x + 2 * y) % 5] for x in range(SIZE)] for y in range(SIZE)]
    g[3][:4] = ['☉'] * 4
    assert matches(g) == {(x, 3) for x in range(4)}


def test_short_or_ragged_grid_raises():
    with pytest.raises(IndexError):
        matches([[0] * SIZE for _ in range(SIZE - 1)])


# ---------- plus_centers() ----------

def test_plus_on_border_row_not_counted():
    g = checker()
    for x in range(5):
        g[0][x] = 9
    for y in range(4):
        g[y][2] = 9
    assert plus_centers(g) == set()  # it's a T: no 'up' arm


def test_double_plus_on_one_long_row():
    g = checker()
    for x in range(SIZE):
        g[3][x] = 9
    for y in range(1, 6):
        g[y][1] = 9
        g[y][5] = 9
    assert plus_centers(g) == {(1, 3), (5, 3)}


def test_solid_4x4_block_counts_as_four_pluses():
    """Documents current behaviour: a solid block yields 4 'plus' crossings (800 bonus)."""
    g = checker()
    for y in range(2, 6):
        for x in range(2, 6):
            g[y][x] = 9
    assert plus_centers(g) == {(3, 3), (4, 3), (3, 4), (4, 4)}


# ---------- swap / legal_moves ----------

def test_swap_is_involution():
    g = checker()
    before = [r[:] for r in g]
    swap(g, (0, 0), (7, 7))
    swap(g, (0, 0), (7, 7))
    assert g == before


def test_legal_moves_does_not_mutate_and_all_moves_valid():
    g = new_grid(Random(3))
    before = [r[:] for r in g]
    moves = legal_moves(g)
    assert g == before
    for a, b in moves:
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
        swap(g, a, b)
        assert matches(g)
        swap(g, a, b)


def test_legal_moves_empty_on_dead_board():
    g = [[(x + 2 * y) % 5 for x in range(SIZE)] for y in range(SIZE)]
    assert legal_moves(g) == []


# ---------- refill ----------

def test_refill_whole_board_produces_valid_kinds():
    g = checker()
    refill(g, {(x, y) for x in range(SIZE) for y in range(SIZE)}, Random(0))
    assert all(0 <= v < KINDS for row in g for v in row)
    assert all(len(r) == SIZE for r in g)


def test_refill_with_empty_cleared_is_noop():
    g = checker()
    before = [r[:] for r in g]
    refill(g, set(), Random(0))
    assert g == before


def test_refill_ignores_out_of_range_cleared():
    g = checker()
    before = [r[:] for r in g]
    refill(g, {(99, 99), (-1, 0)}, Random(0))
    assert g == before


# ---------- Game.attempt boundaries ----------

@pytest.mark.parametrize('a,b', [
    ((-1, 0), (0, 0)), ((0, 0), (0, -1)), ((7, 7), (8, 7)), ((7, 7), (7, 8)),
    ((0, 0), (0, 0)), ((0, 0), (1, 1)), ((0, 0), (2, 0)),
])
def test_attempt_rejects_out_of_range_and_non_adjacent(a, b):
    game = Game(1)
    before = [r[:] for r in game.grid]
    assert game.attempt(a, b) is False
    assert game.grid == before and game.moves == 30


def test_attempt_rejected_while_pending_and_after_game_over():
    game = Game(1)
    a, b = legal_moves(game.grid)[0]
    assert game.attempt(a, b)
    assert game.attempt(*legal_moves(game.grid)[0] if legal_moves(game.grid) else ((0, 0), (1, 0))) is False
    game.pending = set()
    game.moves = 0
    a, b = legal_moves(game.grid)[0]
    assert game.attempt(a, b) is False
    game.moves = -5
    assert game.attempt(a, b) is False


def test_attempt_with_float_coords_is_rejected():
    """Non-integer coordinates are rejected without modifying the board."""
    game = Game(1)
    assert game.attempt((0.5, 0), (1.5, 0)) is False


def test_resolve_without_pending_returns_empty_list():
    """An idle resolution always returns an iterable event list."""
    assert Game(1).resolve() == []


# ---------- scoring ----------

def test_two_separate_fours_get_beyond_four_bonus():
    """README: '25 per cleared symbol, plus 25 for each symbol beyond four'.
    Two independent 4-runs cleared together (8 tiles) get +100 'beyond four' bonus,
    although neither line exceeds four. Expected (per-line reading): 200."""
    game = Game(1)
    game.grid = checker()
    for x in range(4):
        game.grid[0][x] = 9
        game.grid[7][x + 4] = 8
    game.pending = matches(game.grid)
    assert len(game.pending) == 8
    game.resolve()
    assert game.score == 8 * 25, f'score {game.score}'


def test_reachable_two_line_swap_from_real_move():
    """Construct a single swap that completes two separate 4-lines (one horizontal, one vertical,
    not crossing). Shows the bonus can trigger from a normal player move."""
    game = Game(1)
    g = checker()
    # Row 0: A A A _ ; tile at (3,1) is A -> swapping (3,0)<->(3,1) completes row
    # Column 3 below: (3,2),(3,3),(3,4) are B; tile moved down into (3,1) must be B.
    A, B = 7, 8
    g[0][0] = g[0][1] = g[0][2] = A
    g[1][3] = A
    g[0][3] = B
    g[2][3] = g[3][3] = g[4][3] = B
    game.grid = g
    assert game.attempt((3, 0), (3, 1))
    assert len(game.pending) == 8
    game.chain = 0
    game.resolve()
    assert game.score == 200, f'score {game.score} (README per-line rule would give 200)'


def test_cross_score_matches_readme_example():
    # 5x5 plus: 9 unique tiles + two long-line bonuses + one plus = 475
    game = Game(1)
    game.grid = checker()
    for i in range(5):
        game.grid[2][i] = 9
        game.grid[i][2] = 9
    game.pending = matches(game.grid)
    events = game.resolve()
    assert game.score == 475
    assert 'plus' in events and 'match' in events


# ---------- determinism / seeding ----------

@pytest.mark.parametrize('seed', [0, -1, 2**200, 'abc', 'ünïcødé 🜂', 3.5, b'bytes'])
def test_unusual_seeds_are_deterministic(seed):
    g1, g2 = Game(seed), Game(seed)
    assert g1.grid == g2.grid
    first = lambda m: m[0]
    assert play_out(g1, first) == play_out(g2, first)
    assert g1.score == g2.score and g1.grid == g2.grid


def test_seed_none_is_random():
    assert len({tuple(map(tuple, Game().grid)) for _ in range(5)}) > 1


def test_unhashable_seed_raises():
    with pytest.raises(TypeError):
        Game([1, 2])


# ---------- invariants fuzz ----------

def test_fuzz_invariants_many_seeds_random_play():
    r = random.Random(1234)
    shuffles = game_overs = 0
    for seed in range(100):
        game = Game(seed)
        assert not matches(game.grid) and legal_moves(game.grid)
        log = play_out(game, r.choice)
        flat = [e for ev in log for e in ev]
        shuffles += flat.count('shuffle')
        game_overs += flat.count('game_over')
        assert flat.count('game_over') == 1 and 'game_over' in log[-1]
        assert game.moves == 0 and game.score > 0
        assert all(0 <= v < KINDS for row in game.grid for v in row)
    assert game_overs == 100


def test_dead_board_replacement_is_never_dead():
    game = Game(5)
    # force a dead board after resolve by setting grid to a dead layout with a pending set
    dead = [[(x + 2 * y) % game.mode.kinds for x in range(SIZE)] for y in range(SIZE)]
    game.grid = dead
    game.pending = {(0, 0)}
    orig_refill = board.refill
    board.refill = lambda g, c, rng, mode=None: None  # keep the grid dead
    try:
        events = game.resolve()
    finally:
        board.refill = orig_refill
    assert 'shuffle' in events
    assert legal_moves(game.grid) and not matches(game.grid)


def test_dead_board_on_last_move_is_not_shuffled():
    game = Game(5)
    dead = [[(x + 2 * y) % game.mode.kinds for x in range(SIZE)] for y in range(SIZE)]
    game.grid = dead
    game.pending = {(0, 0)}
    game.moves = 0
    orig_refill = board.refill
    board.refill = lambda g, c, rng, mode=None: None
    try:
        events = game.resolve()
    finally:
        board.refill = orig_refill
    assert 'shuffle' not in events and 'game_over' in events


# ---------- performance ----------

def test_perf_new_grid_and_legal_moves():
    t = time.perf_counter()
    for s in range(200):
        new_grid(Random(s))
    per_grid = (time.perf_counter() - t) / 200
    g = new_grid(Random(0))
    t = time.perf_counter()
    for _ in range(200):
        legal_moves(g)
    per_lm = (time.perf_counter() - t) / 200
    print(f'new_grid {per_grid*1000:.2f} ms, legal_moves {per_lm*1000:.2f} ms')
    assert per_grid < 0.25 and per_lm < 0.05  # comfortably below a 16 ms frame for legal_moves


def test_max_score_fits_hud():
    """Greedy best-immediate-score play: does score ever reach 100,000 (where HUD text overlaps 'MOVES')?"""
    best = 0
    for seed in range(10):
        game = Game(seed)
        while game.moves:
            def gain(m):
                g = Game.__new__(Game)
                g.__dict__.update(game.__dict__)
                g.grid = [r[:] for r in game.grid]
                g.rng = Random(); g.rng.setstate(game.rng.getstate())
                g.attempt(*m)
                while g.pending:
                    g.resolve()
                return g.score
            m = max(legal_moves(game.grid), key=gain)
            game.attempt(*m)
            while game.pending:
                game.resolve()
        best = max(best, game.score)
    print('best greedy score', best)
    assert best < 100_000
