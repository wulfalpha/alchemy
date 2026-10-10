import pytest
from alchemy.board import Game, matches, shape_crossings
from alchemy.motion import Motion
from alchemy.scores import Scoreboard, RULES, LEGACY_RULES


def grid_for(kind):
    grid = [[(x+2*y)%5 for x in range(8)] for y in range(8)]
    # Four-by-four L, T, and plus using a distinct value to avoid extra runs.
    row = 0 if kind != 'plus' else 1
    column = 0 if kind == 'l_shape' else 1
    for x in range(4):
        grid[row][x] = 9
    for y in range(4):
        grid[y][column] = 9
    return grid


@pytest.mark.parametrize('kind,bonus', [('l_shape',100),('t_shape',150),('plus',200)])
@pytest.mark.parametrize('turns', range(4))
@pytest.mark.parametrize('chain', [1,2,3])
def test_shape_rotations_scoring_and_exclusive_events(kind, bonus, turns, chain):
    grid = grid_for(kind)
    for _ in range(turns):
        grid = [list(row) for row in zip(*grid[::-1])]
    shapes = shape_crossings(grid)
    assert len(shapes[kind]) == 1
    assert sum(map(len, shapes.values())) == 1
    game = Game(1)
    game.grid = grid
    game.pending = matches(grid)
    game.chain = chain-1
    events = game.resolve()
    assert game.score == (7*25+bonus)*chain
    assert set(events) & {'l_shape','t_shape','plus'} == {kind}


def test_short_line_no_shape_bonus():
    grid = grid_for('l_shape')
    grid[3][0] = 8
    assert not any(shape_crossings(grid).values())


def test_solid_block_classifies_every_crossing_once():
    grid = grid_for('plus')
    for y in range(4):
        for x in range(4):
            grid[y][x] = 9
    shapes = shape_crossings(grid)
    assert {k:len(v) for k,v in shapes.items()} == {'l_shape':4,'t_shape':8,'plus':4}


@pytest.mark.parametrize('side', ['left','right','top','bottom'])
def test_entrance_settles_and_cancels(side):
    motion = Motion()
    motion.entrance(100, side)
    assert motion.active(100)
    assert motion.offset(4,4,100) != (0,0)
    assert not motion.active(420)
    assert motion.offset(4,4,420) == (0,0)
    motion.finish()
    assert motion.offset(4,4,0) == (0,0)


def test_gravity_origins_preserve_survivors():
    motion = Motion()
    motion.fall({(0,2),(0,5)}, 0)
    assert [motion.origins[0,y][1] for y in range(8)] == [-2,-2,-2,-2,-1,-1,0,0]
    assert all(motion.origins[1,y] == (0,0) for y in range(8))


def test_motion_setting_and_score_rules_persist(tmp_path):
    scores = Scoreboard(tmp_path)
    scores.set_reduced_motion(True)
    scores.record('old','Ada',100, rules=LEGACY_RULES)
    scores.record('new','Ada',200)
    scores.close()
    scores = Scoreboard(tmp_path)
    assert scores.reduced_motion()
    assert [r['score'] for r in scores.top()] == [200]
    assert [r['score'] for r in scores.top(rules=LEGACY_RULES)] == [100]
    assert RULES != LEGACY_RULES
    scores.close()
