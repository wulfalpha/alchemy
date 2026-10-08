import pygame
import pytest
from alchemy.board import Game, matched_runs, matches
from alchemy.app import viewport, logical_position


@pytest.mark.parametrize('length,points', [(4,100),(5,150),(6,200),(8,300)])
@pytest.mark.parametrize('chain', [1,2,3])
def test_long_line_score(length, points, chain):
    game = Game(1)
    game.grid = [[(x+2*y)%5 for x in range(8)] for y in range(8)]
    game.grid[0][:length] = [9]*length
    assert len(matched_runs(game.grid)) == 1
    game.pending = matches(game.grid)
    game.chain = chain-1
    game.resolve()
    assert game.score == points*chain
    assert game.last_reaction['length'] == (length-4)*25


def test_hints_cycle_without_changing_experiment():
    game = Game(7)
    from alchemy.board import legal_moves
    options = legal_moves(game.grid)
    state = game.rng.getstate()
    assert [game.hint() for _ in range(len(options)+1)] == options + options[:1]
    assert game.rng.getstate() == state


@pytest.mark.parametrize('size', [(520,390),(1400,800),(800,1000)])
def test_scaled_clicks_and_letterbox(size):
    rect = viewport(size)
    point = (rect.x + rect.width*0.5, rect.y+rect.height*0.5)
    assert logical_position(point, size) == pytest.approx((520,390))
    if rect.x or rect.y:
        assert logical_position((0,0), size) == (-1,-1)
