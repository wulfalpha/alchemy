"""Optional drop-in sound effects. Missing files and audio devices are harmless.

With `tones=True`, events without a sound file fall back to the built-in tones
from `synth.py`; files always win. `sounds` holds only the files that loaded.
"""
import io
import logging
import math
from importlib.resources import files
from .resources import source_directory
from .synth import tones as built_in_tones
from pathlib import Path

import pygame

EVENTS = ('select', 'swap', 'invalid', 'match', 'cascade', 'plus',
          'l_shape', 't_shape', 'hint', 'shuffle', 'restart', 'game_over')


class Audio:
    def __init__(self, directory=None, volume=0.6, muted=False, tones=False):
        volume = float(volume)
        if not math.isfinite(volume):
            raise ValueError("volume must be finite")
        self.muted = muted
        self.sounds = {}
        self.tones = {}
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                return
        roots = ([Path(directory)] if directory is not None else [
            source_directory('sounds'),
            files('alchemy').joinpath('assets', 'sounds'),
        ])
        if directory is not None and not Path(directory).is_dir():
            logging.warning('Sound directory does not exist: %s', directory)
        roots = [root for root in roots if root is not None and root.is_dir()]
        for event in EVENTS:
            for root in roots:
                for extension in ('.wav', '.ogg'):
                    candidates = sorted((p for p in root.iterdir() if p.name.lower() == event + extension and p.is_file()), key=lambda p: p.name)
                    if not candidates:
                        continue
                    path = candidates[0]
                    try:
                        with path.open('rb') as stream:
                            sound = pygame.mixer.Sound(file=stream)
                        sound.set_volume(max(0.0, min(1.0, volume)))
                        self.sounds[event] = sound
                        break
                    except (pygame.error, OSError) as error:
                        logging.warning('Cannot load sound %s: %s', path, error)
                if event in self.sounds:
                    break
        if tones:
            self._load_tones(volume)

    def _load_tones(self, volume):
        missing = [event for event in EVENTS if event not in self.sounds]
        try:
            for event, clip in built_in_tones(missing).items():
                sound = pygame.mixer.Sound(file=io.BytesIO(clip))
                sound.set_volume(max(0.0, min(1.0, volume)))
                self.tones[event] = sound
        except pygame.error as error:
            logging.warning('Cannot use built-in tones: %s', error)

    def play(self, event):
        if not self.muted and pygame.mixer.get_init():
            sound = self.sounds.get(event, self.tones.get(event))
            if sound is not None:
                sound.play()

    def toggle(self):
        self.muted = not self.muted
        if self.muted and pygame.mixer.get_init():
            pygame.mixer.stop()
