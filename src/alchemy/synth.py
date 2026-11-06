"""Built-in metal and glass tones, synthesised at startup so every event has a sound.

The laboratory has two materials. Glassware (vials, flasks) uses the uneven
overtones of a struck glass with a short tap at the onset. Metal (bells, the
crucible) uses FM synthesis: a carrier modulated at an inharmonic 1.4 ratio
whose brightness decays faster than its volume, plus a slightly detuned copy
that beats slowly like a real bell. Clips are returned as in-memory WAV bytes so
pygame converts them to whatever format the mixer opened with. Drop-in sound
files always take priority (see `audio.py`).
"""
from array import array
import io
import math
import random
import sys
import wave

RATE = 22050
VOLUME = 0.3
TAU = 2 * math.pi
GLASS = ((1.0, 1.0), (2.32, 0.5), (4.25, 0.28), (6.63, 0.14))   # (frequency ratio, amplitude)


def note(name):
    """Frequency of a note such as 'C5' or 'F#4' (A4 = 440 Hz); numbers pass through."""
    if not isinstance(name, str):
        return float(name)
    steps = {'C': -9, 'D': -7, 'E': -5, 'F': -4, 'G': -2, 'A': 0, 'B': 2}
    pitch, octave = name[:-1], int(name[-1])
    semitones = steps[pitch[0]] + pitch.count('#') - pitch.count('b') + 12 * (octave - 4)
    return 440.0 * 2 ** (semitones / 12)


def glass(f, t, decay):
    """A struck glass: higher partials fade sooner, leaving a pure ring."""
    return sum(amplitude * math.exp(-decay * (1 + 0.7 * i) * t) * math.sin(TAU * f * ratio * t)
               for i, (ratio, amplitude) in enumerate(GLASS) if f * ratio < RATE / 2)


def metal(f, t, decay, ratio=1.4, depth=3.5):
    """An FM bell: bright at the strike, mellowing as the modulation index decays."""
    index = depth * math.exp(-decay * 1.6 * t)
    ring = math.sin(TAU * f * t + index * math.sin(TAU * f * ratio * t))
    beat = math.sin(TAU * (f + 1.7) * t + 0.6 * index * math.sin(TAU * f * ratio * t))
    return math.exp(-decay * t) * (ring + 0.45 * beat) / 1.45


def clank(f, t, decay):
    """Dull struck metal: a dense, quickly damped spectrum."""
    return metal(f, t, decay, ratio=1.41, depth=7)


VOICES = {'glass': glass, 'metal': metal, 'clank': clank}


def rattle(count, seconds, seed=7):
    """Glass fragments knocking together at random, for a stirred vessel."""
    rng = random.Random(seed)
    return [(rng.uniform(0.02, seconds * 0.7), rng.uniform(1800, 3400), rng.uniform(25, 45), 'glass')
            for _ in range(count)]


# event: (seconds, [(start, note, decay per second, voice)], noise)
FIGURES = {
    'select':    (0.18, [(0.0, 'E7', 30, 'glass')], 0.15),
    'swap':      (0.28, [(0.0, 'C7', 26, 'glass'), (0.07, 'G6', 26, 'glass')], 0.15),
    'invalid':   (0.3, [(0.0, 'C3', 14, 'clank'), (0.1, 'B2', 16, 'clank')], 0.25),
    'match':     (0.9, [(0.0, 'C5', 4.5, 'metal'), (0.0, 'G5', 5, 'metal'), (0.02, 'E6', 9, 'glass')], 0),
    'cascade':   (0.9, [(0.0, 'E5', 4.5, 'metal'), (0.0, 'B5', 5, 'metal'), (0.02, 'G6', 9, 'glass')], 0),
    'l_shape':   (0.8, [(0.0, 'G5', 5, 'metal'), (0.09, 'D6', 6, 'glass')], 0),
    't_shape':   (0.9, [(0.0, 'G5', 5, 'metal'), (0.08, 'B5', 5, 'metal'), (0.16, 'D6', 6, 'glass')], 0),
    'plus':      (1.3, [(0.0, 'C5', 3.5, 'metal'), (0.07, 'G5', 4, 'metal'), (0.14, 'C6', 5, 'glass'),
                        (0.21, 'E6', 5, 'glass'), (0.28, 'G6', 5, 'glass')], 0),
    'unstable':  (0.5, [(0.0, 'E6', 8, 'glass'), (0.06, 'B6', 8, 'glass'), (0.12, 'E7', 10, 'glass')], 0),
    'line_burst': (0.8, [(0.0, 'D4', 6, 'clank'), (0.03, 'A5', 5, 'metal'), (0.08, 'D6', 7, 'glass')], 0.3),
    'square_burst': (0.9, [(0.0, 'G3', 5, 'clank'), (0.02, 'D5', 4.5, 'metal'), (0.1, 'G5', 6, 'glass')], 0.35),
    'element_burst': (1.4, [(0.0, 'C3', 3, 'clank'), (0.0, 'C4', 3, 'metal'), (0.1, 'G4', 3.5, 'metal'),
                            (0.2, 'C6', 5, 'glass'), (0.3, 'G6', 5, 'glass'), (0.4, 'C7', 6, 'glass')], 0.4),
    'hint':      (0.4, [(0.0, 'B6', 12, 'glass'), (0.08, 'F#7', 14, 'glass')], 0),
    'shuffle':   (0.7, rattle(9, 0.7), 0.35),
    'restart':   (1.1, [(0.0, 'G3', 3, 'metal'), (0.12, 'C4', 3, 'metal')], 0),
    'game_over': (2.0, [(0.0, 'C3', 1.6, 'metal'), (0.0, 'G4', 2.2, 'metal'), (0.3, 'C5', 2, 'metal'),
                        (0.3, 'E5', 2.2, 'metal'), (0.45, 'G6', 4, 'glass'), (0.6, 'C7', 4, 'glass')], 0),
}


def render(seconds, notes, noise=0.0, rate=RATE):
    """Mix the notes and an optional noise tap or swell into 16-bit mono samples."""
    length = int(seconds * rate)
    mix = [0.0] * length
    for start, pitch, decay, voice in notes:
        base, sound = note(pitch), VOICES[voice]
        for offset in range(int(start * rate), length):
            t = (offset - start * rate) / rate
            mix[offset] += min(1.0, t / 0.002) * sound(base, t, decay)
    if noise:
        # A struck tap for short sounds; a swelling stir for long ones.
        rng, smooth = random.Random(7), 0.0
        tap = seconds < 0.5
        for offset in range(length):
            white = rng.uniform(-1, 1)
            smooth += 0.08 * (white - smooth)                     # one-pole low-pass
            if tap:
                mix[offset] += noise * (white - smooth) * math.exp(-offset / (0.004 * rate))
            else:
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
