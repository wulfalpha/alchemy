"""Fixed plates: authored boards with no reserves, no stirs, a swap limit, and swap medals."""
import sys
from dataclasses import replace
from pathlib import Path

from alchemy.adventure import PURIFY, AdventureGame, Experiment, parse_layout, saved_medal
from alchemy.board import LINE
from alchemy.medals import swap_medal
from alchemy.modes import ELEMENTS
from alchemy.scores import SWAPS_ORDER, ranking_order

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from solve_plate import solve  # noqa: E402

EMPTY = '.' * 8
# Swapping (3, 7) with (4, 7) lines up four fire on the bottom row; the water and air
# above then fall but make nothing.
ONE_SWAP = (EMPTY,) * 6 + ('...wa...', 'fffaf...')
PLATE = Experiment(key='adventure-plate-test-v1', title='Test Plate', reserves=(0, 0, 0, 0), unstable=True,
                   objective=PURIFY, element=0, layout=ONE_SWAP, swap_limit=3, medal_by='swaps',
                   medals=(2, 1))


def test_layout_letters_are_element_initials():
    grid = parse_layout(('fw..', 'ae..'), ELEMENTS)
    assert grid == [[0, 1, None, None], [2, 3, None, None]]


def test_a_plate_opens_on_its_layout_and_symbols_with_nothing_in_reserve():
    marks = (((0, 7), LINE),)
    game = AdventureGame(experiment=replace(PLATE, marks=marks))
    assert game.grid == parse_layout(ONE_SWAP, ELEMENTS)
    assert game.unstable == {(0, 7): LINE}
    assert game.material_left == game.initial_material == 7
    assert game.swaps_remaining == 3


def test_solving_a_plate_wins_with_a_swap_medal():
    game = AdventureGame(experiment=PLATE)
    assert game.attempt((3, 7), (4, 7))
    while game.pending:
        game.resolve()
    assert game.outcome == 'success' and game.turns == 1 and game.medal == 'Gold'


def test_running_out_of_swaps_stalls():
    layout = (EMPTY,) * 5 + ('...w....', '...a....', 'fffaf.f.')
    game = AdventureGame(experiment=replace(PLATE, layout=layout, swap_limit=1))
    assert game.attempt((3, 7), (4, 7))
    while game.pending:
        game.resolve()
    assert game.outcome == 'stalled' and game.failure_reason == 'swaps_exhausted'
    assert 'No swaps left' in game.message and '1 fire left' in game.message


def test_a_blocked_plate_is_never_stirred():
    game = AdventureGame(experiment=replace(PLATE, layout=(EMPTY,) * 7 + ('fwfwfwfw',)))
    before = [row[:] for row in game.grid]
    events = []
    game._settle(events)
    assert game.outcome == 'stalled' and game.failure_reason == 'plate_blocked'
    assert game.grid == before and game.stirs == 0
    assert 'No reaction is left on the plate' in game.message


def test_swap_medals_and_saved_medals():
    assert [swap_medal(n, (5, 4)) for n in (3, 4, 5, 6)] == ['Gold', 'Gold', 'Silver', 'Bronze']
    assert swap_medal(None, (5, 4)) is None
    assert saved_medal('adventure-first-v2', 50, 99) == 'Gold'          # material, v1 thresholds
    assert saved_medal('unknown-key', 10, 1) == 'Bronze'


def test_plates_rank_by_fewest_swaps():
    assert ranking_order('adventure-plate-red-v1') == SWAPS_ORDER
    assert ranking_order('adventure-first-v3').startswith('material_left')
    assert ranking_order('classic-30').startswith('score')


def test_the_solver_finds_the_fewest_swaps():
    best, lines, _ = solve(PLATE)
    assert (best, lines) == (1, [(((3, 7), (4, 7)),)])
    assert solve(replace(PLATE, layout=(EMPTY,) * 7 + ('fwfwfwfw',)))[0] is None
