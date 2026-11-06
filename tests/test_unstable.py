"""Unstable symbols: earned by 5-runs and shapes, detonated by a later match."""
from alchemy.adventure import AdventureGame
from alchemy.board import (ELEMENT, LINE, SIZE, SQUARE, UNSTABLE_POINTS, Game, blast_cells, detonate,
                           fall_positions, matched_runs, shape_crossings, unstable_births)
from alchemy.modes import CLASSIC, DIAGONALS
from alchemy.scores import RULES, score_categories


def quiet():
    """A four-symbol board with no line of four in any direction."""
    return [[(x + 2*y) % 4 for x in range(SIZE)] for y in range(SIZE)]


def births_for(grid, swapped=()):
    runs = matched_runs(grid, CLASSIC)
    return unstable_births(runs, shape_crossings(grid, CLASSIC, runs), swapped)


def test_quiet_board_has_no_matches():
    assert matched_runs(quiet(), CLASSIC) == []
    assert matched_runs(quiet(), DIAGONALS) == []


def test_run_of_four_earns_nothing():
    grid = quiet()
    grid[3][:4] = [0] * 4
    assert births_for(grid) == {}


def test_run_of_five_earns_a_line_on_the_swapped_cell():
    grid = quiet()
    grid[3][:5] = [0] * 5
    assert births_for(grid, swapped=((1, 3), (1, 4))) == {(1, 3): LINE}
    assert births_for(grid) == {(2, 3): LINE}   # cascades: the middle of the run


def test_run_of_six_or_more_earns_a_square():
    for length in (6, 7, 8):
        grid = quiet()
        grid[3][:length] = [0] * length
        assert list(births_for(grid).values()) == [SQUARE]


def test_l_and_t_earn_an_element_at_the_crossing_and_nothing_for_their_runs():
    grid = quiet()
    grid[4][:5] = [0] * 5            # a five...
    for y in range(1, 5):
        grid[y][0] = 0               # ...meeting a vertical four at its end: an L
    assert births_for(grid) == {(0, 4): ELEMENT}
    grid = quiet()
    grid[4][:5] = [0] * 5
    for y in range(1, 5):
        grid[y][1] = 0               # ending inside the five: a T
    assert births_for(grid) == {(1, 4): ELEMENT}


def test_a_long_line_inside_a_shape_earns_only_the_shapes_element():
    grid = quiet()
    grid[4][:6] = [0] * 6            # a six (alone it would earn a Square)...
    for y in range(1, 5):
        grid[y][0] = 0               # ...ending an L
    assert births_for(grid) == {(0, 4): ELEMENT}


def test_plus_earns_an_element():
    grid = quiet()
    grid[3][1:5] = [0] * 4
    for y in range(2, 6):
        grid[y][2] = 0
    assert births_for(grid) == {(2, 3): ELEMENT}


def test_line_blast_follows_the_given_directions():
    grid = quiet()
    assert blast_cells(grid, (2, 3), LINE, ((1, 0),)) == {(x, 3) for x in range(SIZE)}
    assert blast_cells(grid, (2, 3), LINE, ((0, 1),)) == {(2, y) for y in range(SIZE)}
    assert blast_cells(grid, (2, 3), LINE, ((1, 1),)) == {(x, x+1) for x in range(SIZE-1)}


def test_square_blast_is_clipped_at_the_edge_and_skips_empty_cells():
    grid = quiet()
    assert blast_cells(grid, (0, 0), SQUARE) == {(0, 0), (1, 0), (0, 1), (1, 1)}
    grid[1][1] = None
    assert (1, 1) not in blast_cells(grid, (0, 0), SQUARE)
    assert len(blast_cells(grid, (4, 4), SQUARE)) == 9


def test_element_blast_takes_every_symbol_of_its_element():
    grid = quiet()
    cells = blast_cells(grid, (0, 0), ELEMENT)
    assert cells == {(x, y) for y in range(SIZE) for x in range(SIZE) if grid[y][x] == grid[0][0]}
    assert len(cells) == 16


def test_detonation_chains_into_other_unstable_symbols():
    grid = quiet()
    grid[3][:4] = [0] * 4
    runs = matched_runs(grid, CLASSIC)
    unstable = {(1, 3): LINE, (6, 3): SQUARE}
    cleared, detonated = detonate(grid, runs, unstable)
    assert detonated == unstable
    assert {(x, 3) for x in range(SIZE)} <= cleared                     # the row
    assert {(x, y) for x in (5, 6, 7) for y in (2, 3, 4)} <= cleared     # the chained square
    assert len(cleared) == 8 + 6


def test_chained_line_clears_its_row_and_column():
    grid = quiet()
    grid[3][:4] = [0] * 4
    unstable = {(0, 3): SQUARE, (1, 2): LINE}      # the square catches the line
    cleared, detonated = detonate(grid, matched_runs(grid, CLASSIC), unstable)
    assert (1, 2) in detonated
    assert {(x, 2) for x in range(SIZE)} | {(1, y) for y in range(SIZE)} <= cleared


def test_fall_positions_match_gravity():
    grid = quiet()
    landing = fall_positions(grid, {(0, 5), (0, 6)})
    assert landing[0, 4] == (0, 6) and landing[0, 7] == (0, 7) and landing[0, 0] == (0, 2)
    assert (0, 5) not in landing and landing[1, 3] == (1, 3)


def classic_with_five():
    """A Classic game one swap away from a horizontal five on row 3.

    The test board is too regular to stay playable after a refill, so the
    dead-board check is switched off to inspect the reaction itself.
    """
    game = Game(3, CLASSIC)
    game._settle = lambda events: None
    game.grid = quiet()
    game.grid[3][:5] = [0, 0, 1, 0, 0]
    game.grid[4][2] = 0
    return game


def test_swapped_five_leaves_a_line_symbol_that_survives_the_refill():
    game = classic_with_five()
    assert game.attempt((2, 3), (2, 4))
    events = game.resolve()
    assert 'unstable' in events
    assert (2, 3) not in game.last_cleared
    assert game.unstable == {(2, 3): LINE}   # nothing below it was cleared, so it stays put
    assert game.grid[3][2] == 0


def test_matching_a_line_symbol_clears_the_row_and_scores_the_blast():
    game = Game(3, CLASSIC)
    game._settle = lambda events: None
    game.grid = quiet()
    game.grid[3][:4] = [0, 0, 0, 1]
    game.grid[4][3] = 0
    game.unstable = {(0, 3): LINE}
    assert game.attempt((3, 3), (3, 4))
    assert game.pending == {(x, 3) for x in range(SIZE)}   # the board shows the whole blast
    events = game.resolve()
    assert 'line_burst' in events
    assert game.last_reaction['base'] == 4 * 25
    assert game.last_reaction['unstable'] == 4 * UNSTABLE_POINTS
    assert game.last_reaction['total'] == 4 * 25 + 4 * UNSTABLE_POINTS
    assert 'Line burst' in game.message
    assert game.unstable == {}   # a run of four earns nothing; the line symbol is spent


def test_unstable_symbols_move_with_swaps_and_failed_swaps_restore_them():
    game = Game(3, CLASSIC)
    game.grid = quiet()
    game.unstable = {(0, 0): SQUARE}
    assert not game.attempt((0, 0), (1, 0))
    assert game.unstable == {(0, 0): SQUARE}
    game._swap((0, 0), (1, 0))
    assert game.unstable == {(1, 0): SQUARE}


def test_a_fresh_board_has_no_unstable_symbols(monkeypatch):
    import alchemy.board
    game = Game(3, CLASSIC)
    game.unstable = {(0, 0): ELEMENT}
    real = alchemy.board.legal_moves
    calls = []

    def dead_once(grid, mode=None):   # report the current board dead, then behave normally
        calls.append(1)
        return [] if len(calls) == 1 else real(grid, mode)

    monkeypatch.setattr(alchemy.board, 'legal_moves', dead_once)
    events = []
    game._settle(events)
    assert events == ['shuffle'] and game.unstable == {}


def test_diagonal_and_adventure_never_form_unstable_symbols():
    for game in (Game(3, DIAGONALS), AdventureGame()):
        game.grid = quiet()
        game.grid[3][:5] = [0, 0, 1, 0, 0]
        game.grid[4][2] = 0
        assert game.attempt((2, 3), (2, 4))
        while game.pending:
            assert 'unstable' not in game.resolve()
        assert game.unstable == {}


def test_classic_keeps_its_previous_scores_one_tab_away():
    categories = score_categories(CLASSIC.key, CLASSIC.label, CLASSIC.rules)
    assert categories[0].rules == CLASSIC.rules != RULES
    assert categories[1].rules == RULES and categories[1].mode == CLASSIC.key
    assert len(categories) == 6
    assert DIAGONALS.rules == RULES
