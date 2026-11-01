"""Built-in placeholder tones, synthesised at startup so every event has a sound.

Each event is a short bell-like figure: notes built from a few inharmonic partials
with fast attacks and exponential decay. Clips are returned as in-memory WAV
bytes so pygame converts them to whatever format the mixer opened with.
Drop-in sound files always take priority (see `audio.py`).
"""
from array import array
import io
import math
import random
import sys
import wave

RATE = 22050
VOLUME = 0.32
BELL = ((1.0, 1.0), (2.76, 0.4), (5.4, 0.15))   # (frequency ratio, amplitude)
PURE = ((1.0, 1.0),)


def note(name):
    """Frequency of a note such as 'C5' or 'F#4' (A4 = 440 Hz)."""
    steps = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}
    pitch, octave = name[:-1], int(name[-1])
    semitones = steps[pitch[0]] + pitch.count('#') - pitch.count('b') + 12 * (octave - 4)
    return 440.0 * 2 ** (semitones / 12)


# event: (seconds, [(start, note, decay per second, partials)], noise)
FIGURES = {
    'select':    (0.09, [(0.0, 'A5', 40, PURE)], 0),
    'swap':      (0.18, [(0.0, 'E5', 22, PURE), (0.06, 'A5', 22, PURE)], 0),
    'invalid':   (0.22, [(0.0, 'D3', 18, BELL), (0.09, 'C#3', 18, BELL)], 0),
    'match':     (0.55, [(0.0, 'C5', 7, BELL), (0.0, 'E5', 8, BELL), (0.0, 'G5', 9, BELL)], 0),
    'cascade':   (0.55, [(0.0, 'E5', 7, BELL), (0.0, 'G5', 8, BELL), (0.0, 'C6', 9, BELL)], 0),
    'l_shape':   (0.5, [(0.0, 'G5', 8, BELL), (0.08, 'D6', 8, BELL)], 0),
    't_shape':   (0.6, [(0.0, 'G5', 8, BELL), (0.07, 'B5', 8, BELL), (0.14, 'D6', 8, BELL)], 0),
    'plus':      (0.8, [(0.0, 'C6', 6, BELL), (0.06, 'E6', 6, BELL), (0.12, 'G6', 6, BELL),
                        (0.18, 'C7', 5, BELL)], 0),
    'hint':      (0.25, [(0.0, 'E6', 14, PURE), (0.05, 'B6', 14, PURE)], 0),
    'shuffle':   (0.45, [], 0.5),
    'restart':   (0.6, [(0.0, 'G4', 6, BELL), (0.1, 'C5', 6, BELL)], 0),
    'game_over': (1.2, [(0.0, 'G4', 3, BELL), (0.0, 'D5', 3, BELL), (0.25, 'C5', 2.5, BELL),
                        (0.25, 'E5', 2.5, BELL), (0.25, 'G5', 2.5, BELL)], 0),
}


def render(seconds, notes, noise=0.0, rate=RATE):
    """Mix the notes (and optional swelling noise) into 16-bit mono samples."""
    length = int(seconds * rate)
    mix = [0.0] * length
    for start, name, decay, partials in notes:
        base = note(name)
        for offset in range(int(start * rate), length):
            t = (offset - start * rate) / rate
            envelope = min(1.0, t / 0.004) * math.exp(-decay * t)
            mix[offset] += envelope * sum(amplitude * math.sin(2 * math.pi * base * ratio * t)
                                          for ratio, amplitude in partials if base * ratio < rate / 2)
    if noise:
        rng, smooth = random.Random(7), 0.0
        for offset in range(length):
            smooth += 0.08 * (rng.uniform(-1, 1) - smooth)       # one-pole low-pass
            mix[offset] += noise * 4 * smooth * math.sin(math.pi * offset / length)
    peak = max(1.0, max(map(abs, mix), default=0.0))
    fade = int(0.01 * rate)                                       # no click at the end
    samples = array('h', (int(32767 * VOLUME * value / peak * min(1.0, (length - i) / fade))
                          for i, value in enumerate(mix)))
    if sys.byteorder == 'big':
        samples.byteswap()                                        # WAV is little-endian
    return samples


def wav(samples, rate=RATE):
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(rate)
        clip.writeframes(samples.tobytes())
    return buffer.getvalue()


def tones(events):
    """WAV bytes for every requested event that has a built-in figure."""
    return {event: wav(render(*FIGURES[event])) for event in events if event in FIGURES}
