"""CLI and headless app-loop edge cases for alchemy.app (SDL dummy drivers set in tests/conftest.py)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pygame
import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
ENV = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
           PYTHONPATH=str(REPO / 'src'))


def run(*args, env=None, cwd=None, timeout=60):
    return subprocess.run([PY, '-m', 'alchemy', *args], capture_output=True, text=True,
                          env=env or ENV, cwd=cwd, timeout=timeout, stdin=subprocess.DEVNULL)


# ---------- CLI argument validation (subprocess, non-TTY) ----------

@pytest.mark.parametrize('args', [
    ['--volume', 'abc'], ['--volume', '-0.1'], ['--volume', '1.01'], ['--volume', 'nan'],
    ['--volume', 'inf'], ['--seed', 'abc'], ['--seed', '1.5'], ['--bogus'], ['--volume'],
])
def test_bad_args_exit_2_with_usage(args):
    r = run(*args)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert 'usage:' in r.stderr and 'Traceback' not in r.stderr


@pytest.mark.parametrize('args', [
    ['--seed', '-1'], ['--seed', str(2**100)], ['--volume', '0'], ['--volume', '1'],
    ['--mute'], ['--sound-dir', '/nonexistent/dir'], ['--sound-dir', '/etc/passwd'],
])
def test_odd_but_valid_args_smoke(args):
    r = run('--smoke-test', *args)
    assert r.returncode == 0, r.stderr
    assert r.stdout == ''  # quiet on non-TTY


def test_help_works_without_display():
    r = run('--help', env=dict(ENV, SDL_VIDEODRIVER='nonexistent-driver'))
    assert r.returncode == 0 and '--smoke-test' in r.stdout


def test_screenshot_formats(tmp_path):
    for name in ('a.png', 'b.jpg', 'c.bmp', 'ü 🜂.png'):
        r = run('--smoke-test', '--seed', '1', '--screenshot', str(tmp_path / name))
        assert r.returncode == 0, r.stderr
        assert (tmp_path / name).stat().st_size > 0


def test_screenshot_without_extension_is_not_png(tmp_path):
    out = tmp_path / 'shot'
    r = run('--smoke-test', '--screenshot', str(out))
    assert r.returncode == 0
    head = out.read_bytes()[:8]
    print('extensionless screenshot header:', head)
    assert head != b'\x89PNG\r\n\x1a\n'  # documents: saved as TGA despite help saying PNG


@pytest.mark.xfail(strict=True, reason='--screenshot into missing dir shows traceback, see improvements.md')
def test_screenshot_into_missing_dir_gives_clean_error(tmp_path):
    r = run('--smoke-test', '--screenshot', str(tmp_path / 'nope' / 'x.png'))
    print(r.returncode, r.stderr[-300:])
    assert 'Traceback' not in r.stderr, 'unhandled exception surfaces to user'


def test_same_seed_same_screenshot_across_hash_seeds(tmp_path):
    shots = []
    for hs in ('0', '1', '12345'):
        p = tmp_path / f's{hs}.png'
        r = run('--smoke-test', '--seed', '42', '--screenshot', str(p), env=dict(ENV, PYTHONHASHSEED=hs))
        assert r.returncode == 0
        shots.append(pygame.image.tostring(pygame.image.load(str(p)), 'RGB'))
    assert shots[0] == shots[1] == shots[2]


@pytest.mark.xfail(strict=True, reason='no display shows raw traceback, see improvements.md')
def test_no_video_device_gives_clean_error():
    env = dict(ENV, SDL_VIDEODRIVER='nonexistent-driver')
    env.pop('DISPLAY', None); env.pop('WAYLAND_DISPLAY', None)
    r = run('--smoke-test', env=env)
    print(r.returncode, r.stderr[-300:])
    assert r.returncode != 0
    assert 'Traceback' not in r.stderr, 'raw pygame traceback shown when no display is available'


def test_works_from_other_cwd(tmp_path):
    assert run('--smoke-test', cwd=tmp_path).returncode == 0


# ---------- asset handling (copy of repo so the original is untouched) ----------

@pytest.fixture
def repo_copy(tmp_path):
    dst = tmp_path / 'repo'
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns('.venv', '.git', '__pycache__', '.pytest_cache'))
    return dst


def run_copy(repo, *args):
    return run(*args, env=dict(ENV, PYTHONPATH=str(repo / 'src')))


def test_missing_custom_image_falls_back(repo_copy):
    (repo_copy / 'img' / 'fire.png').unlink()
    assert run_copy(repo_copy, '--smoke-test').returncode == 0


def test_missing_img_dir_falls_back(repo_copy):
    shutil.rmtree(repo_copy / 'img')
    assert run_copy(repo_copy, '--smoke-test').returncode == 0


@pytest.mark.xfail(strict=True, reason='bad custom image crashes instead of falling back, see improvements.md')
def test_corrupt_custom_image_falls_back(repo_copy):
    (repo_copy / 'img' / 'fire.png').write_bytes(b'not a png')
    r = run_copy(repo_copy, '--smoke-test')
    print(r.returncode, r.stderr[-300:])
    assert r.returncode == 0, 'corrupt custom PNG crashes startup instead of using packaged fallback'


@pytest.mark.xfail(strict=True, reason='bad custom image crashes instead of falling back, see improvements.md')
def test_empty_custom_image_falls_back(repo_copy):
    (repo_copy / 'img' / 'water.png').write_bytes(b'')
    r = run_copy(repo_copy, '--smoke-test')
    assert r.returncode == 0, 'zero-byte custom PNG crashes startup'


@pytest.mark.xfail(strict=True, reason='bad custom image crashes instead of falling back, see improvements.md')
def test_directory_named_like_image_falls_back(repo_copy):
    (repo_copy / 'img' / 'air.png').unlink()
    (repo_copy / 'img' / 'air.png').mkdir()
    r = run_copy(repo_copy, '--smoke-test')
    assert r.returncode == 0, 'img/air.png being a directory crashes startup (exists() vs is_file())'


def test_odd_custom_images_ok(repo_copy, tmp_path):
    pygame.init()
    s = pygame.Surface((1, 1)); s.fill((255, 0, 0))
    pygame.image.save(s, str(repo_copy / 'img' / 'fire.png'))           # 1x1, no alpha
    big = pygame.Surface((4000, 300), pygame.SRCALPHA)                   # huge, non-square
    pygame.image.save(big, str(repo_copy / 'img' / 'sun.png'))
    pal = pygame.Surface((64, 64), depth=8)                              # 8-bit palette
    pygame.image.save(pal, str(repo_copy / 'img' / 'earth.png'))
    jpg = pygame.Surface((64, 64)); pygame.image.save(jpg, str(tmp_path / 'x.jpg'))
    shutil.copy(tmp_path / 'x.jpg', repo_copy / 'img' / 'water.png')     # JPEG named .png
    assert run_copy(repo_copy, '--smoke-test').returncode == 0


def test_all_assets_missing_errors(repo_copy):
    shutil.rmtree(repo_copy / 'img')
    for p in (repo_copy / 'src' / 'alchemy' / 'assets').glob('*.png'):
        p.unlink()
    r = run_copy(repo_copy, '--smoke-test')
    print(r.returncode, r.stderr[-200:])
    assert r.returncode != 0  # expected failure; check it is at least understandable


# ---------- scripted in-process game loop ----------

class FakeClock:
    def tick(self, *_):
        return 16


def drive(script, argv=('--seed', '7'), max_frames=20000):
    """Run app.main() with a scripted event source. `script(frame, state)` returns events."""
    import alchemy.app as app
    from alchemy.board import Game
    games = []

    class RecGame(Game):
        def __init__(self, *a, **k):
            super().__init__(*a, **k); games.append(self)

    state = {'frame': 0, 'games': games}

    def fake_get():
        state['frame'] += 1
        if state['frame'] > max_frames:
            return [pygame.event.Event(pygame.QUIT)]
        return script(state['frame'], state)

    with patch.object(app, 'Game', RecGame), \
         patch('pygame.event.get', fake_get), \
         patch('pygame.time.get_ticks', lambda: state['frame'] * 400), \
         patch('pygame.time.Clock', FakeClock), \
         patch.object(sys, 'argv', ['alchemy', *argv]):
        app.main()
    return state


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode='', scancode=0)


def click(cell, button=1):
    x, y = cell
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(48 + x * 70 + 35, 154 + y * 70 + 35), button=button)


def click_px(pos, button=1):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def test_play_full_game_by_hint_and_clicks_then_game_over_inputs():
    from alchemy.board import legal_moves
    queue = []

    def script(frame, st):
        g = st['games'][-1]
        if queue:
            return [queue.pop(0)]
        if g.pending:
            return []
        if g.moves:
            a, b = legal_moves(g.grid)[0]
            queue.extend([click(b)])
            return [key(pygame.K_h), click(a)]
        if not st.get('done'):
            st['done'] = True
            st['final'] = (g.score, g.moves)
            # game over: hint, clicks, right clicks, mute should all be harmless
            return [key(pygame.K_h), click((0, 0)), click((1, 0)), click((0, 0), 3),
                    click_px((5, 5)), click_px((1039, 779)), click_px((662, 600)),
                    key(pygame.K_m), key(pygame.K_m)]
        return [pygame.event.Event(pygame.QUIT)]

    st = drive(script)
    assert st['final'][1] == 0 and st['final'][0] > 0
    assert len(st['games']) == 1


def test_restart_mid_cascade_and_with_seed_repeats_same_board():
    from alchemy.board import legal_moves

    def script(frame, st):
        g = st['games'][-1]
        if frame == 1:
            a, b = legal_moves(g.grid)[0]
            return [click(a), click(b)]
        if frame == 2:
            assert g.pending
            return [key(pygame.K_r)]
        if frame == 3:
            return [click_px((818 + 10, 590 + 10))]  # New game button
        return [pygame.event.Event(pygame.QUIT)]

    st = drive(script)
    gs = st['games']
    assert len(gs) == 3
    assert not gs[-1].pending and gs[-1].moves == 30
    # documents UX: with --seed, every "New game" is the identical board
    assert gs[1].grid == gs[2].grid


def test_clicks_on_tile_gaps_and_board_edges():
    def script(frame, st):
        if frame == 1:
            return [click_px((48, 154)), click_px((48 + 560 - 1, 154 + 560 - 1)),
                    click_px((48 + 560, 154)), click_px((47, 153)), click_px((0, 0))]
        return [pygame.event.Event(pygame.QUIT)]
    drive(script)


def test_hint_is_always_the_same_move():
    hints = []
    from alchemy.board import legal_moves

    def script(frame, st):
        if frame <= 3:
            hints.append(legal_moves(st['games'][-1].grid)[0])
            return [key(pygame.K_h)]
        return [pygame.event.Event(pygame.QUIT)]
    drive(script)
    assert len(set(hints)) == 1


@pytest.mark.xfail(strict=True, raises=IndexError, reason='hint on a dead board raises IndexError (possible bug), see improvements.md')
def test_hint_on_dead_board_does_not_crash():
    """Possible bug: app.py:72/80 index legal_moves()[0] without a guard (unreachable today)."""
    def script(frame, st):
        g = st['games'][-1]
        if frame == 1:
            g.grid = [[(x + 2 * y) % 5 for x in range(8)] for y in range(8)]  # dead board
            return [key(pygame.K_h)]
        return [pygame.event.Event(pygame.QUIT)]
    drive(script)
