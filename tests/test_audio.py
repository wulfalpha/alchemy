import os
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
import pygame
from alchemy.audio import Audio


class AudioTests(unittest.TestCase):
    def tearDown(self):
        pygame.mixer.quit()

    def test_load_play_mute_and_missing_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            with wave.open(str(Path(directory) / 'plus.wav'), 'wb') as clip:
                clip.setnchannels(1)
                clip.setsampwidth(2)
                clip.setframerate(22050)
                clip.writeframes(b'\x00\x00' * 2205)
            audio = Audio(directory, volume=0.4)
            self.assertIn('plus', audio.sounds)
            audio.play('plus')
            self.assertGreater(audio.sounds['plus'].get_num_channels(), 0)
            audio.toggle()
            self.assertEqual(audio.sounds['plus'].get_num_channels(), 0)
            audio.play('plus')
            self.assertEqual(audio.sounds['plus'].get_num_channels(), 0)
            audio.play('missing')
            audio.toggle()
            audio.play('plus')
            self.assertGreater(audio.sounds['plus'].get_num_channels(), 0)

    def test_bad_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'match.wav').write_text('not audio')
            with self.assertLogs(level='WARNING'):
                audio = Audio(directory)
            self.assertFalse(audio.sounds)

    def test_unavailable_device_is_harmless(self):
        with patch('pygame.mixer.get_init', return_value=None), patch('pygame.mixer.init', side_effect=pygame.error('no device')):
            audio = Audio()
            audio.play('match')
            audio.toggle()
            self.assertFalse(audio.sounds)


class ToneTests(unittest.TestCase):
    def tearDown(self):
        pygame.mixer.quit()

    def test_tones_fill_every_event_without_files(self):
        from alchemy.audio import EVENTS
        with tempfile.TemporaryDirectory() as directory:
            audio = Audio(directory, volume=0.5, tones=True)
        self.assertEqual(audio.sounds, {})
        self.assertEqual(set(audio.tones), set(EVENTS))
        for sound in audio.tones.values():
            self.assertGreater(sound.get_length(), 0.05)
            self.assertAlmostEqual(sound.get_volume(), 0.5, places=2)
        audio.play('match')
        self.assertGreater(audio.tones['match'].get_num_channels(), 0)
        audio.toggle()
        self.assertEqual(audio.tones['match'].get_num_channels(), 0)

    def test_sound_file_takes_priority_over_tone(self):
        with tempfile.TemporaryDirectory() as directory:
            with wave.open(str(Path(directory) / 'match.wav'), 'wb') as clip:
                clip.setnchannels(1)
                clip.setsampwidth(2)
                clip.setframerate(22050)
                clip.writeframes(b'\x00\x00' * 2205)
            audio = Audio(directory, tones=True)
        self.assertIn('match', audio.sounds)
        self.assertNotIn('match', audio.tones)
        self.assertIn('swap', audio.tones)
        audio.play('match')
        self.assertGreater(audio.sounds['match'].get_num_channels(), 0)

    def test_tones_are_off_by_default_and_without_a_device(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(Audio(directory).tones, {})
        with patch('pygame.mixer.get_init', return_value=None), patch('pygame.mixer.init', side_effect=pygame.error('no device')):
            self.assertEqual(Audio(tones=True).tones, {})

    def test_tone_clips_are_valid_bounded_wav(self):
        import io
        from alchemy.synth import FIGURES, tones
        clips = tones(FIGURES)
        for event, clip in clips.items():
            with wave.open(io.BytesIO(clip)) as reader:
                self.assertEqual((reader.getnchannels(), reader.getsampwidth()), (1, 2))
                self.assertAlmostEqual(reader.getnframes() / reader.getframerate(), FIGURES[event][0], places=2)
        self.assertEqual(tones(['select']), {'select': clips['select']})  # deterministic
