"""The campaign: authored kits that unlock in order, with progress saved locally."""
from types import SimpleNamespace

import pygame
import pytest

import alchemy.app as app
from alchemy.adventure import (CAMPAIGN_KITS, DETONATE, EXPERIMENTS, PREVIOUS_EXPERIMENTS, PURIFY,
                               medal_thresholds)
from alchemy.board import ELEMENT
from alchemy.audio import Audio
from alchemy.modes import CAMPAIGN, MODES
from alchemy.scores import Scoreboard, ranking_order


@pytest.fixture(autouse=True)
def display():
    pygame.init()
    pygame.display.set_mode((10, 10))
    yield


def session(tmp_path, mode=CAMPAIGN.key):
    args = SimpleNamespace(seed=None, assets_dir=None, player='Tester', smoke_test=True, mode=mode)
    return app.Session(args, Scoreboard(tmp_path), Audio(muted=True))


def press(s, k):
    s.handle(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode='', scancode=0), (1040, 780))


def win(s):
    s.game.outcome = 'success'
    s.record_score()


@pytest.fixture
def two_stages():
    """The second stage, which the first unlocks."""
    return CAMPAIGN_KITS[1]


# ---------- definitions ----------

def test_kits_are_distinct_efficiency_ranked_experiments_with_their_own_medals():
    keys = [kit.experiment.key for kit in CAMPAIGN_KITS]
    assert len(set(keys)) == len(keys)
    others = {e.key for e in (*EXPERIMENTS.values(), *PREVIOUS_EXPERIMENTS.values())}
    for kit in CAMPAIGN_KITS:
        experiment = kit.experiment
        assert experiment.key not in others
        assert ranking_order(experiment.key).startswith('material_left')
        assert medal_thresholds(experiment.key) == experiment.medals
        assert experiment.unstable and experiment.stir_limit
        assert kit.stage and kit.lesson


def test_the_dry_flask_is_scarce_in_water_only():
    flask = CAMPAIGN_KITS[0].experiment
    assert CAMPAIGN_KITS[0].stage == 'Nigredo'
    assert flask.reserves == (20, 8, 20, 20)
    assert (flask.target, flask.stir_limit, flask.medals) == (3500, 8, (30, 40))


def test_purification_starts_with_an_earth_element_and_a_small_earth_reserve():
    kit = CAMPAIGN_KITS[1]
    purification = kit.experiment
    assert kit.stage == 'Albedo' and purification.objective == PURIFY
    assert purification.element == 3 and purification.reserves == (20, 20, 20, 12)
    assert purification.start_unstable == ((3, ELEMENT),)
    assert (purification.stir_limit, purification.medals) == (8, (30, 40))


def test_the_golden_shape_asks_for_three_detonations():
    kit = CAMPAIGN_KITS[2]
    shape = kit.experiment
    assert kit.stage == 'Citrinitas' and shape.objective == DETONATE and shape.detonations == 3
    assert shape.reserves == (12,)*4 and (shape.stir_limit, shape.medals) == (8, (40, 50))


def test_every_stage_starts_and_draws(tmp_path):
    from alchemy.render import Canvas, draw
    scores = Scoreboard(tmp_path)
    scores.unlock_campaign(len(CAMPAIGN_KITS))
    s = session(tmp_path)
    canvas = Canvas()
    for index in range(len(CAMPAIGN_KITS)):
        s.kit_index = index
        s.start_new_game()
        assert s.game.experiment is CAMPAIGN_KITS[index].experiment
        assert CAMPAIGN_KITS[index].lesson in s.game.message
        draw(canvas, s)
        s.game.outcome, s.game.failure_reason = 'stalled', 'stirs_exhausted'
        draw(canvas, s)


def test_campaign_is_an_adventure_mode():
    assert MODES[CAMPAIGN.key].moves is None and CAMPAIGN.key in MODES


# ---------- saved progress ----------

def test_progress_starts_at_one_only_grows_and_survives_reopening(tmp_path):
    scores = Scoreboard(tmp_path)
    assert scores.campaign_unlocked() == 1
    assert scores.unlock_campaign(2) is True
    assert scores.unlock_campaign(2) is False
    assert scores.unlock_campaign(1) is False
    scores.close()
    assert Scoreboard(tmp_path).campaign_unlocked() == 2


def test_unavailable_scores_keep_the_first_stage_open(tmp_path):
    scores = Scoreboard(tmp_path)
    scores.close()
    assert scores.campaign_unlocked() == 1 and scores.unlock_campaign(3) is False


# ---------- playing ----------

def test_campaign_starts_on_the_first_stage_with_its_lesson(tmp_path):
    s = session(tmp_path)
    assert s.adventure and s.campaign and s.kit is CAMPAIGN_KITS[0]
    assert s.game.experiment is CAMPAIGN_KITS[0].experiment
    assert s.game.mode.unstable
    assert CAMPAIGN_KITS[0].lesson in s.game.message
    assert s.tagline().startswith('Stage 1 of')
    assert s.categories()[0].label == 'Nigredo: The Dry Flask / current'


def test_e_with_one_open_stage_explains_how_to_unlock(tmp_path):
    s = session(tmp_path)
    game = s.game
    press(s, pygame.K_e)
    assert s.game is game and 'unlock the next' in game.message


def test_e_does_nothing_outside_the_campaign(tmp_path):
    s = session(tmp_path, mode='adventure-5')
    game = s.game
    press(s, pygame.K_e)
    assert s.game is game and s.kit is None


def test_a_win_saves_the_score_and_unlocks_the_next_stage(tmp_path, two_stages):
    s = session(tmp_path)
    win(s)
    assert s.score_saved
    assert s.scores.top(s.score_seed(), mode=CAMPAIGN_KITS[0].experiment.key)
    assert s.scores.campaign_unlocked() == 2
    assert 'Albedo unlocked' in s.game.message


def test_a_stalled_run_unlocks_nothing(tmp_path, two_stages):
    s = session(tmp_path)
    s.game.outcome = 'stalled'
    s.record_score()
    assert s.scores.campaign_unlocked() == 1


def test_e_cycles_open_stages_and_asks_before_abandoning(tmp_path, two_stages):
    s = session(tmp_path)
    s.scores.unlock_campaign(2)
    s.kit_index = 0
    s.start_new_game()
    press(s, pygame.K_e)
    assert s.kit is two_stages and s.game.experiment is two_stages.experiment
    s.swapped = True                     # a game in progress
    press(s, pygame.K_e)
    assert s.confirming == 'kit' and s.kit is two_stages
    press(s, pygame.K_e)
    assert s.kit is CAMPAIGN_KITS[0]     # wrapped around to the first stage


def test_reopening_resumes_at_the_newest_open_stage(tmp_path, two_stages):
    Scoreboard(tmp_path).unlock_campaign(2)
    assert session(tmp_path).kit is two_stages
