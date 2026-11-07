"""The campaign: authored kits that unlock in order, with progress saved locally."""
from dataclasses import replace
from types import SimpleNamespace

import pygame
import pytest

import alchemy.app as app
from alchemy.adventure import (CAMPAIGN_KITS, CHAPTERS, DETONATE, EXPERIMENTS, PREVIOUS_EXPERIMENTS, PURIFY,
                               chapter_of, experiment_medal, medal_thresholds, saved_medal)
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
        assert medal_thresholds(experiment.key) == experiment.medals
        assert experiment.unstable and kit.stage and kit.lesson
        if experiment.layout:                      # a fixed plate: a swap-limited puzzle
            assert ranking_order(experiment.key).startswith('swaps')
            assert experiment.swap_limit and experiment.medal_by == 'swaps'
            assert experiment.reserves == (0, 0, 0, 0)
        else:
            assert ranking_order(experiment.key).startswith('material_left')
            assert experiment.stir_limit and experiment.medal_by == 'material'


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


def test_the_red_plate_is_proven_solvable_and_needs_its_symbols():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from solve_plate import solve
    kit = CAMPAIGN_KITS[3]
    plate = kit.experiment
    assert kit.stage == 'Rubedo' and plate.objective == PURIFY and plate.element == 0
    best, lines, _ = solve(plate)
    silver, gold = plate.medals
    assert best == gold == 5 and silver == 6 and plate.swap_limit == 7 and len(lines) == 1
    assert solve(replace(plate, marks=()))[0] is None


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
    assert s.tagline().startswith('Chapter 1: stage 1 of')
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


# ---------- progression after a win ----------

def finish(s):
    s.motion.finish()
    s.game.outcome = 'success'
    s.record_score()


def test_enter_on_the_win_screen_begins_the_next_stage(tmp_path):
    s = session(tmp_path)
    finish(s)
    assert s.stage_won and s.next_kit is CAMPAIGN_KITS[1] and not s.chapter_complete
    assert 'Press Enter' in s.game.message
    press(s, pygame.K_RETURN)
    assert s.kit is CAMPAIGN_KITS[1] and s.game.experiment is CAMPAIGN_KITS[1].experiment
    assert not s.game.finished


def test_clicking_the_win_screen_begins_the_next_stage(tmp_path):
    s = session(tmp_path)
    finish(s)
    s.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(300, 400)), (1040, 780))
    assert s.kit is CAMPAIGN_KITS[1]


def test_a_stalled_run_offers_no_next_stage(tmp_path):
    s = session(tmp_path)
    s.motion.finish()
    s.game.outcome = 'stalled'
    s.record_score()
    assert not s.stage_won and s.next_kit is None
    press(s, pygame.K_RETURN)
    assert s.kit is CAMPAIGN_KITS[0]


def test_the_last_stage_completes_the_chapter_and_keeps_progress_for_later_stages(tmp_path):
    s = session(tmp_path)
    s.scores.unlock_campaign(len(CAMPAIGN_KITS))
    s.kit_index = len(CAMPAIGN_KITS) - 1
    s.start_new_game()
    finish(s)
    assert s.chapter_complete and s.next_kit is None
    assert s.scores.campaign_unlocked() == len(CAMPAIGN_KITS) + 1
    assert s.unlocked_kits() == len(CAMPAIGN_KITS)
    press(s, pygame.K_RETURN)
    assert s.kit is CAMPAIGN_KITS[-1] and s.game.finished


def test_stage_medals_show_each_stages_best_win(tmp_path):
    s = session(tmp_path)
    assert s.stage_medals == [None] * len(CAMPAIGN_KITS)
    s.scores.record('a', 'T', 4000, 42, mode=CAMPAIGN_KITS[0].experiment.key, rules=s.mode.rules,
                    material_left=10, swaps=30, stirs=0)
    s.scores.record('b', 'T', 4000, 42, mode=CAMPAIGN_KITS[0].experiment.key, rules=s.mode.rules,
                    material_left=45, swaps=30, stirs=0)
    s.reload_scores()
    assert s.stage_medals[0] == 'Gold' and s.stage_medals[1:] == [None] * (len(CAMPAIGN_KITS) - 1)


# ---------- chapters ----------

RED_PLATE, BURNING = 3, 4      # the last stage of Chapter 1 and the first of Chapter 2


def test_chapters_hold_the_stages_in_unlock_order():
    assert [chapter.name for chapter in CHAPTERS] == ['Chapter 1', 'Chapter 2']
    assert [c.title for c in CHAPTERS] == ['The Great Work', 'The Tria Prima']
    assert CAMPAIGN_KITS == tuple(kit for chapter in CHAPTERS for kit in chapter.kits)
    assert chapter_of(RED_PLATE) == (CHAPTERS[0], 0)
    assert chapter_of(BURNING) == (CHAPTERS[1], 4)
    with pytest.raises(IndexError):
        chapter_of(len(CAMPAIGN_KITS))


def test_the_burning_gives_two_stirs_and_gold_only_without_stirring():
    kit = CAMPAIGN_KITS[BURNING]
    burning = kit.experiment
    assert kit.stage == 'Sulfur' and burning.title == 'The Burning'
    assert burning.stir_limit == 2 and burning.gold_stirs == 0 and burning.objective == 'points'
    assert experiment_medal(burning, 5, 30, stirs=0) == 'Gold'
    assert experiment_medal(burning, 45, 30, stirs=1) == 'Silver'
    assert experiment_medal(burning, 39, 30, stirs=2) == 'Bronze'
    assert experiment_medal(burning, 45, 30) == 'Silver'           # stirs unknown: no Gold
    assert saved_medal(burning.key, 45, 30, 0) == 'Gold'
    assert saved_medal(burning.key, 45, 30, 1) == 'Silver'


def test_a_stir_gated_gold_still_shows_as_the_stages_best_medal(tmp_path):
    s = session(tmp_path)
    key = CAMPAIGN_KITS[BURNING].experiment.key
    s.scores.record('a', 'T', 4000, 42, mode=key, rules=s.mode.rules, material_left=50, swaps=30, stirs=2)
    s.scores.record('b', 'T', 4000, 42, mode=key, rules=s.mode.rules, material_left=12, swaps=30, stirs=0)
    s.reload_scores()
    assert s.stage_medals[BURNING] == 'Gold'


def test_finishing_chapter_1_leads_into_chapter_2(tmp_path):
    s = session(tmp_path)
    s.scores.unlock_campaign(RED_PLATE + 1)
    s.kit_index = RED_PLATE
    s.start_new_game()
    finish(s)
    assert s.chapter_complete and s.next_kit is CAMPAIGN_KITS[BURNING]
    assert 'Sulfur unlocked' in s.game.message
    press(s, pygame.K_RETURN)
    assert s.kit is CAMPAIGN_KITS[BURNING] and not s.game.finished
    assert s.tagline() == f'Chapter 2: stage 1 of {len(CHAPTERS[1].kits)}'
    assert s.chapter() == (CHAPTERS[1], BURNING)


def test_players_who_finished_chapter_1_find_chapter_2_open(tmp_path):
    Scoreboard(tmp_path).unlock_campaign(RED_PLATE + 2)       # recorded past the old last stage
    assert session(tmp_path).kit is CAMPAIGN_KITS[BURNING]


QUICKSILVER = 5


def test_quicksilver_swaps_and_matches_diagonally():
    from alchemy.adventure import AdventureGame
    from alchemy.board import legal_moves
    from alchemy.modes import ADVENTURE, DIAGONAL
    kit = CAMPAIGN_KITS[QUICKSILVER]
    assert kit.stage == 'Mercury' and kit.experiment.diagonal
    assert kit.experiment.objective == DETONATE and kit.experiment.detonations == 5
    game = AdventureGame(experiment=kit.experiment)
    assert game.mode.directions == game.mode.swaps == DIAGONAL and game.mode.unstable
    diagonal = [(a, b) for a, b in legal_moves(game.grid, game.mode) if a[0] != b[0] and a[1] != b[1]]
    assert diagonal and diagonal[0] not in legal_moves(game.grid, ADVENTURE)
    assert game.attempt(*diagonal[0])
    plain = AdventureGame(experiment=CAMPAIGN_KITS[BURNING].experiment)
    assert plain.mode.swaps == plain.mode.directions != DIAGONAL


def test_a_diagonal_line_symbol_blasts_its_whole_diagonal():
    from alchemy.board import LINE, detonate, matched_runs, unstable_births, shape_crossings
    from alchemy.modes import DIAGONAL, ADVENTURE
    mode = replace(ADVENTURE, directions=DIAGONAL, swaps=DIAGONAL, unstable=True)
    grid = [[(x + 2*y) % 4 for x in range(8)] for y in range(8)]   # no runs in any direction
    for i in range(1, 5):
        grid[i][i] = 1
    runs = matched_runs(grid, mode)
    assert runs == [[(1, 1), (2, 2), (3, 3), (4, 4)]]
    cleared, detonated = detonate(grid, runs, {(2, 2): LINE})
    assert detonated == {(2, 2): LINE} and cleared == {(i, i) for i in range(8)}
    grid[5][5] = 1                                                 # five in a diagonal: a Line forms
    runs = matched_runs(grid, mode)
    assert list(unstable_births(runs, shape_crossings(grid, mode, runs)).values()) == [LINE]


def test_clicking_a_diagonal_neighbour_swaps_only_in_quicksilver(tmp_path):
    from alchemy.board import legal_moves
    s = session(tmp_path)
    s.scores.unlock_campaign(QUICKSILVER + 1)
    for index, swaps in ((BURNING, False), (QUICKSILVER, True)):
        s.kit_index = index
        s.start_new_game()
        s.motion.finish()
        moves = legal_moves(s.game.grid, s.game.mode)
        a, b = next(((a, b) for a, b in moves if a[0] != b[0] and a[1] != b[1]), ((0, 0), (1, 1)))
        s.select(a)
        s.select(b)
        assert (s.game.turns == 1) is swaps


def test_win_and_chapter_screens_draw(tmp_path):
    from alchemy.render import Canvas, draw
    canvas = Canvas()
    s = session(tmp_path)
    finish(s)
    draw(canvas, s)
    s.scores.unlock_campaign(len(CAMPAIGN_KITS))
    s.kit_index = len(CAMPAIGN_KITS) - 1
    s.start_new_game()
    finish(s)
    draw(canvas, s)
    s.kit_index = RED_PLATE                       # Chapter 1 complete, Chapter 2 offered
    s.start_new_game()
    finish(s)
    assert s.chapter_complete and s.next_kit
    draw(canvas, s)


# ---------- undo on the plate ----------

def test_u_undoes_swaps_on_the_red_plate_one_at_a_time(tmp_path):
    s = session(tmp_path)
    s.scores.unlock_campaign(4)
    s.kit_index = 3
    s.start_new_game()
    s.motion.finish()
    start = [row[:] for row in s.game.grid]
    press(s, pygame.K_u)
    assert s.game.message == 'Nothing to undo.'
    positions = []
    for move in (((6, 2), (7, 2)), ((6, 6), (6, 7))):     # the solution's opening swaps
        positions.append([row[:] for row in s.game.grid])
        assert s.game.attempt(*move)
        while s.game.pending:
            s.game.resolve()
    assert s.game.turns == 2
    press(s, pygame.K_u)
    assert s.game.grid == positions[1] and s.game.turns == 1
    press(s, pygame.K_u)
    assert s.game.grid == start == positions[0] and s.game.turns == 0


def test_u_does_nothing_outside_plates(tmp_path):
    s = session(tmp_path)
    s.motion.finish()
    message = s.game.message
    press(s, pygame.K_u)
    assert s.game.message == message


def test_clicking_salt_explains_instead_of_selecting(tmp_path):
    s = session(tmp_path)
    s.scores.unlock_campaign(7)
    s.kit_index = 6
    s.start_new_game()
    s.motion.finish()
    x, y = CAMPAIGN_KITS[6].experiment.salt[0]
    s.press_cell((x, y))
    assert s.selected is None and "Salt can't be moved" in s.game.message
