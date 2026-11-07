"""Experiment objectives other than a points target: purify an element, detonate an Element."""
from dataclasses import replace

from alchemy.adventure import DETONATE, FIRST_EXPERIMENT, POINTS, PURIFY, AdventureGame
from alchemy.board import ELEMENT, LINE, SQUARE, matches

EARTH = 3
PURIFY_KIT = replace(FIRST_EXPERIMENT, key='test-purify', objective=PURIFY, element=EARTH,
                     reserves=(0, 0, 0, 0), unstable=True)
DETONATE_KIT = replace(FIRST_EXPERIMENT, key='test-detonate', objective=DETONATE,
                       reserves=(0, 0, 0, 0), unstable=True)


def empty(game):
    game.grid = [[None]*8 for _ in range(8)]
    return game


def react(game):
    game.pending = matches(game.grid)
    while game.pending:
        game.resolve()


def test_points_is_the_default_objective():
    game = AdventureGame()
    assert game.experiment.objective == POINTS
    assert game.objective_title == 'Target: 3,500 points'
    assert game.objective_progress == '3,500 points to go'
    assert game.shortfall == '3,500 points short'
    assert 'reach 3,500 points' in game.message


# ---------- purify ----------

def test_purify_counts_board_and_reserve_and_describes_itself():
    game = AdventureGame(experiment=replace(PURIFY_KIT, reserves=(0, 0, 0, 5)))
    on_board = sum(v == EARTH for row in game.grid for v in row)
    assert game.element_left == on_board + 5
    assert game.objective_title == 'Goal: remove all earth'
    assert game.objective_progress.startswith(f'{on_board + 5} earth left')
    assert 'remove every earth tile' in game.message


def test_purify_succeeds_when_the_last_earth_is_matched_even_with_points_short():
    game = empty(AdventureGame(experiment=PURIFY_KIT))
    for x in range(4):
        game.grid[7][x] = EARTH
    game.grid[7][5] = game.grid[6][5] = 0          # other material may remain
    react(game)
    assert game.outcome == 'success' and game.score < FIRST_EXPERIMENT.target
    assert 'free of earth' in game.message


def test_purify_is_not_met_while_earth_remains_in_the_reserve():
    game = empty(AdventureGame(experiment=replace(PURIFY_KIT, reserves=(0, 0, 0, 1))))
    for x in range(4):
        game.grid[7][x] = EARTH
    react(game)
    assert game.outcome != 'success'
    assert game.element_left == 1 and game.shortfall == '1 earth left'


def test_purify_failure_names_the_earth_left():
    game = empty(AdventureGame(experiment=PURIFY_KIT))
    game.grid[7][0] = game.grid[7][2] = EARTH       # no match possible
    events = []
    game._settle(events)
    assert game.outcome == 'stalled' and '2 earth left' in game.message


# ---------- detonate ----------

def test_detonate_counts_symbols_and_says_how_to_progress():
    game = AdventureGame(experiment=replace(DETONATE_KIT, detonations=3))
    game.unstable = {}
    assert game.objective_title == 'Goal: detonate 3 unstable'
    assert game.objective_progress == '0 of 3 detonated; form symbols with 5+ in a row'
    game.unstable = {(0, 0): LINE}
    assert game.objective_progress == '0 of 3 detonated; match a symbol to set it off'
    assert game.shortfall == '0 of 3 detonated'


def line_blast(game, tier=LINE):
    empty(game)
    for x in range(4):
        game.grid[7][x] = 0
    game.unstable = {(0, 7): tier}
    react(game)


def test_detonating_enough_symbols_of_any_kind_wins():
    game = AdventureGame(experiment=DETONATE_KIT)
    line_blast(game)
    assert game.detonations == 1 and game.outcome == 'success'
    assert 'symbols are spent' in game.message


def test_points_alone_do_not_win_a_detonate_objective():
    game = AdventureGame(experiment=replace(DETONATE_KIT, target=1, detonations=2))
    line_blast(game, ELEMENT)
    assert game.detonations == 1 and game.outcome != 'success'
    assert game.shortfall == '1 of 2 detonated'


def test_a_chained_detonation_counts_each_symbol():
    game = empty(AdventureGame(experiment=replace(DETONATE_KIT, detonations=2)))
    for x in range(4):
        game.grid[7][x] = 0
    game.grid[7][6] = 1
    game.unstable = {(0, 7): LINE, (6, 7): SQUARE}  # the row blast reaches (6, 7)
    react(game)
    assert game.detonations == 2 and game.outcome == 'success'


# ---------- symbols on the opening board ----------

def test_start_symbols_sit_on_tiles_of_their_element():
    game = AdventureGame(experiment=replace(PURIFY_KIT, start_unstable=((EARTH, ELEMENT),)))
    assert list(game.unstable.values()) == [ELEMENT]
    (x, y), = game.unstable
    assert game.grid[y][x] == EARTH and not game.pending


def test_an_earth_element_blast_purifies_the_board():
    game = empty(AdventureGame(experiment=PURIFY_KIT))
    for x in range(4):
        game.grid[7][x] = EARTH
    game.grid[2][6] = game.grid[4][7] = EARTH      # stranded: too few to match
    game.unstable = {(0, 7): ELEMENT}
    react(game)
    assert game.element_left == 0 and game.outcome == 'success'
