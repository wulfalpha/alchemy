"""Award boundaries, completion timing, and compatibility with saved scores."""
from dataclasses import replace
from unittest.mock import Mock

import pytest

from alchemy.adventure import AdventureGame, FIRST_EXPERIMENT, EXPERIMENTS
from alchemy.board import matches
from alchemy.medals import efficiency_medal
from alchemy.render import AdventureView
from alchemy.scores import Scoreboard


@pytest.mark.parametrize('material, medal', [
    (None, None), (0, 'Bronze'), (15, 'Bronze'), (29, 'Bronze'),
    (30, 'Silver'), (44, 'Silver'), (45, 'Gold'), (144, 'Gold'),
])
def test_award_boundaries(material, medal):
    assert efficiency_medal(material) == medal


@pytest.mark.parametrize('experiment', EXPERIMENTS.values())
def test_medals_require_success_and_ignore_stirs(experiment):
    game = AdventureGame(experiment=experiment)
    assert game.medal is None
    game.outcome = 'stalled'
    assert game.medal is None
    game.outcome = 'success'
    assert game.medal == 'Gold'
    game.stirs = 8
    assert game.medal == 'Gold'


def test_medal_uses_material_after_entire_winning_cascade():
    game = AdventureGame(experiment=replace(FIRST_EXPERIMENT, target=1, reserves=(4, 0, 0, 0)))
    game.grid = [[None]*8 for _ in range(8)]
    for x in range(4):
        game.grid[7][x] = 1
    game.pending = matches(game.grid)
    game.resolve()
    assert game.score >= game.experiment.target and game.pending
    assert game.medal is None
    game.resolve()
    assert game.medal == 'Bronze' and game.material_left == 0


def test_saved_medals_survive_reopening_without_changing_ranking(tmp_path):
    scores = Scoreboard(tmp_path)
    mode = EXPERIMENTS['adventure-5'].key
    for name, material in [('bronze', 15), ('gold', 45), ('silver', 30), ('legacy', None)]:
        scores.record(name, name, 3500, 42, mode=mode, material_left=material, swaps=20, stirs=2)
    scores.close()
    scores = Scoreboard(tmp_path)
    rows = scores.top(42, mode=mode)
    assert [row['id'] for row in rows] == ['gold', 'silver', 'bronze', 'legacy']
    assert [efficiency_medal(row['material_left']) for row in rows] == ['Gold', 'Silver', 'Bronze', None]
    scores.close()


def test_rendered_legacy_score_does_not_invent_a_medal():
    canvas = Mock()
    AdventureView().score_detail(canvas, dict(material_left=None), 282)
    shown = ' '.join(str(call.args[0]) for call in canvas.text.call_args_list)
    assert 'Efficiency stats unavailable' in shown
    assert not any(medal in shown for medal in ('Bronze', 'Silver', 'Gold'))


@pytest.mark.parametrize('material, medal', [
    (39, 'Bronze'), (40, 'Silver'), (49, 'Silver'), (50, 'Gold'),
])
def test_unstable_revisions_use_raised_thresholds(material, medal):
    for experiment in EXPERIMENTS.values():
        game = AdventureGame(experiment=experiment)
        game.outcome = 'success'
        game.reserves = [0, 0, 0, 0]
        cells = [(x, y) for y in range(8) for x in range(8)]
        for x, y in cells[material:]:
            game.grid[y][x] = None
        assert game.material_left == material
        assert game.medal == medal


def test_released_revisions_keep_their_original_thresholds():
    from alchemy.adventure import PREVIOUS_EXPERIMENTS, medal_thresholds
    for experiment in PREVIOUS_EXPERIMENTS.values():
        assert medal_thresholds(experiment.key) == (30, 45)
    assert medal_thresholds('adventure-first-v1') == (30, 45)
    assert medal_thresholds(EXPERIMENTS['adventure'].key) == (40, 50)


@pytest.mark.parametrize('released, medal', [(True, 'Silver'), (False, 'Bronze')])
def test_scoreboard_grades_each_category_by_its_own_revision(released, medal):
    from alchemy.adventure import PREVIOUS_EXPERIMENTS
    from alchemy.scores import ScoreCategory
    key = (PREVIOUS_EXPERIMENTS if released else EXPERIMENTS)['adventure-5'].key
    canvas = Mock()
    AdventureView().score_detail(canvas, dict(material_left=35, swaps=20, stirs=1), 282,
                                 ScoreCategory('Adventure', key, 'shapes-v3'))
    assert f'35 / {medal}' in [call.args[0] for call in canvas.text.call_args_list]


def test_material_counter_shows_the_current_revisions_goals():
    note = AdventureView().counter(AdventureGame(experiment=EXPERIMENTS['adventure']))[2]
    assert note == 'Silver 40+ / Gold 50+'
