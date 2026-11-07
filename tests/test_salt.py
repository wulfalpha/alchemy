"""Salt: inert tiles that fall but never match or swap; water matches and blasts dissolve them."""
from dataclasses import replace

from alchemy.adventure import CAMPAIGN_KITS, DISSOLVE, AdventureGame, Experiment, dissolved_salt, stir
from alchemy.board import LINE, SALT, legal_moves, matches
from alchemy.modes import ADVENTURE

FIRE, WATER, AIR, EARTH = range(4)
SALTY = Experiment(key='adventure-salt-test-v1', title='Salt Test', seed=42, unstable=True, stir_limit=8,
                   objective=DISSOLVE, dissolver=WATER, salt=((3, 6),))


def calm():
    """A board with no runs in any direction: (x + 2y) mod 4."""
    return [[(x + 2*y) % 4 for x in range(8)] for y in range(8)]


def settle(game):
    while game.pending:
        game.resolve()


def test_salt_never_matches_and_cannot_be_swapped():
    grid = calm()
    grid[0][:4] = [SALT] * 4
    assert not matches(grid, ADVENTURE)
    game = AdventureGame(experiment=SALTY)
    assert game.grid[6][3] == SALT and game.salt_left == 1
    assert all(SALT not in (game.grid[a[1]][a[0]], game.grid[b[1]][b[0]])
               for a, b in legal_moves(game.grid, game.mode))
    assert not game.attempt((3, 6), (3, 7)) and not game.attempt((2, 6), (3, 6))


def test_salt_is_not_material():
    game = AdventureGame(experiment=SALTY)
    plain = AdventureGame(experiment=replace(SALTY, salt=()))
    assert game.material_left == plain.material_left - 1


def test_a_water_match_beside_salt_dissolves_it_and_a_fire_match_does_not():
    grid = calm()
    grid[4][0:4] = [WATER] * 4              # a water run on row 4, salt just below (2, 5)
    grid[5][2] = SALT
    assert dissolved_salt(grid, ADVENTURE, WATER) == {(2, 5)}
    assert dissolved_salt(grid, ADVENTURE, FIRE) == set()
    assert dissolved_salt(grid, ADVENTURE, None) == set()
    grid[5][2] = SALT
    grid[3][5] = SALT                       # diagonal to the run's end: not touching
    assert dissolved_salt(grid, ADVENTURE, WATER) == {(2, 5)}


def test_dissolving_the_last_salt_wins_and_is_not_counted_as_consumed():
    game = AdventureGame(experiment=replace(SALTY, salt=()))
    game.grid = calm()
    game.grid[4][0:3] = [WATER] * 3
    game.grid[3][3] = WATER                 # swap (3, 3) down into (3, 4) to make four
    game.grid[5][1] = SALT
    assert game.salt_left == 1
    assert game.attempt((3, 3), (3, 4))
    assert (1, 5) in game.pending
    settle(game)
    assert game.salt_left == 0 and game.outcome == 'success'
    assert game.consumed == 4
    assert 'salt is dissolved' in game.message


def test_clearing_salt_sounds_a_dissolve():
    game = AdventureGame(experiment=replace(SALTY, salt=()))
    game.grid = calm()
    game.grid[4][0:3] = [WATER] * 3
    game.grid[3][3] = WATER
    game.grid[5][1] = SALT
    game.grid[2][7] = SALT                  # far away, so the game goes on
    assert game.attempt((3, 3), (3, 4))
    events = game.resolve()
    assert events[:2] == ['match', 'dissolve']


def test_a_blast_dissolves_salt():
    game = AdventureGame(experiment=replace(SALTY, salt=(), dissolver=None))
    game.grid = calm()
    game.grid[4][0:3] = [FIRE] * 3
    game.grid[3][3] = FIRE
    game.grid[4][6] = SALT                  # further along row 4, which the Line clears
    game.unstable = {(1, 4): LINE}
    assert game.attempt((3, 3), (3, 4))
    assert (6, 4) in game.pending
    settle(game)
    assert game.salt_left == 0


def test_salt_falls_when_the_tile_below_clears():
    game = AdventureGame(experiment=replace(SALTY, salt=(), dissolver=None, reserves=(0, 0, 0, 0), stir_limit=0))
    game.grid = calm()
    game.grid[4][0:3] = [FIRE] * 3
    game.grid[3][3] = FIRE
    game.grid[3][1] = SALT                  # sits on (1, 4), which the fire run clears
    assert game.attempt((3, 3), (3, 4))
    game.resolve()
    assert game.grid[4][1] == SALT


def test_a_stir_keeps_every_salt_tile():
    game = AdventureGame(experiment=CAMPAIGN_KITS[6].experiment)
    before = game.salt_left
    assert stir(game.grid, game.rng, game.mode)
    assert game.salt_left == before and not matches(game.grid, game.mode)


def test_fixation_is_the_salt_stage():
    kit = CAMPAIGN_KITS[6]
    fixation = kit.experiment
    assert kit.stage == 'Salt' and fixation.title == 'Fixation'
    assert fixation.objective == DISSOLVE and fixation.dissolver == WATER and len(fixation.salt) == 6
    game = AdventureGame(experiment=fixation)
    assert game.salt_left == 6 and 'water' in game.objective_progress
    assert legal_moves(game.grid, game.mode)
