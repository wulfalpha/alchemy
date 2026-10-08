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
