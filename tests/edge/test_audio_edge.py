"""Edge-case tests for alchemy.audio."""
import logging
import os
import wave
from pathlib import Path
from unittest.mock import patch

import pygame
import pytest

from alchemy.audio import Audio, EVENTS


@pytest.fixture(autouse=True)
def _quit_mixer():
    yield
    pygame.mixer.quit()


def write_wav(path, frames=2205):
    with wave.open(str(path), 'wb') as clip:
        clip.setnchannels(1); clip.setsampwidth(2); clip.setframerate(22050)
        clip.writeframes(b'\x00\x00' * frames)


def test_nonexistent_sound_dir_is_silent_and_no_warning(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        audio = Audio(tmp_path / 'does-not-exist')
    assert audio.sounds == {}
    assert not caplog.records  # documents: user typo in --sound-dir gets no feedback


def test_sound_dir_is_a_file(tmp_path):
    f = tmp_path / 'file.txt'; f.write_text('x')
    assert Audio(f).sounds == {}


def test_unicode_and_space_dir(tmp_path):
    d = tmp_path / 'sön ds 🜂'; d.mkdir()
    write_wav(d / 'match.wav')
    assert 'match' in Audio(d).sounds


def test_all_events_load(tmp_path):
    for e in EVENTS:
        write_wav(tmp_path / f'{e}.wav')
    assert set(Audio(tmp_path).sounds) == set(EVENTS)


def test_wav_priority_over_ogg_and_bad_wav_falls_back(tmp_path):
    write_wav(tmp_path / 'match.wav')
    (tmp_path / 'match.ogg').write_bytes(b'junk')
    a = Audio(tmp_path)
    assert a.sounds['match'].get_length() == pytest.approx(0.1, abs=0.02)
    # corrupt wav + good wav-in-ogg-name? pygame sniffs content, so a wav named .ogg loads
    (tmp_path / 'match.wav').write_bytes(b'not audio')
    write_wav(tmp_path / 'match.ogg')
    a = Audio(tmp_path)
    assert 'match' in a.sounds


def test_empty_and_zero_frame_files(tmp_path):
    (tmp_path / 'select.wav').write_bytes(b'')
    write_wav(tmp_path / 'swap.wav', frames=0)
    a = Audio(tmp_path)
    assert 'select' not in a.sounds  # skipped with warning, no crash


def test_uppercase_extension_not_found(tmp_path):
    write_wav(tmp_path / 'match.WAV')
    assert 'match' not in Audio(tmp_path).sounds  # documents case-sensitivity


def test_directory_named_like_sound(tmp_path):
    (tmp_path / 'match.wav').mkdir()
    assert Audio(tmp_path).sounds == {}


@pytest.mark.parametrize('vol,expected', [(-1, 0.0), (0, 0.0), (0.4, 0.4), (1, 1.0), (5, 1.0)])
def test_volume_clamped(tmp_path, vol, expected):
    write_wav(tmp_path / 'match.wav')
    assert Audio(tmp_path, volume=vol).sounds['match'].get_volume() == pytest.approx(expected, abs=0.01)


def test_nan_volume_via_api(tmp_path):
    write_wav(tmp_path / 'match.wav')
    a = Audio(tmp_path, volume=float('nan'))
    v = a.sounds['match'].get_volume()
    print('nan volume ->', v)


def test_string_volume_via_api_raises_typeerror(tmp_path):
    write_wav(tmp_path / 'match.wav')
    with pytest.raises(TypeError):
        Audio(tmp_path, volume='0.5')


def test_mute_start_and_toggle_without_mixer(tmp_path):
    write_wav(tmp_path / 'match.wav')
    a = Audio(tmp_path, muted=True)
    a.play('match')
    assert a.sounds['match'].get_num_channels() == 0
    pygame.mixer.quit()
    a.play('match'); a.toggle(); a.toggle()  # mixer gone: must not raise


def test_play_unknown_and_none_event(tmp_path):
    a = Audio(tmp_path)
    a.play('nope'); a.play(None)


def test_many_rapid_plays_overlap(tmp_path):
    write_wav(tmp_path / 'match.wav', frames=22050)
    a = Audio(tmp_path)
    for _ in range(100):
        a.play('match')
    assert a.sounds['match'].get_num_channels() >= 1


def test_mixer_init_failure_with_existing_files(tmp_path):
    write_wav(tmp_path / 'match.wav')
    with patch('pygame.mixer.get_init', return_value=None), \
         patch('pygame.mixer.init', side_effect=pygame.error('no device')):
        a = Audio(tmp_path)
        a.play('match'); a.toggle()
    assert a.sounds == {}
