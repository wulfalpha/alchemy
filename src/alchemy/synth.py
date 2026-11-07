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


# Noise voices read fixed, seeded tables so every clip is reproducible.
_noise = random.Random(11)
WHITE = [_noise.uniform(-1, 1) for _ in range(RATE * 3)]
BROWN, _level = [], 0.0
for _value in WHITE:
    _level += 0.02 * (_value - _level)                        # one-pole low-pass: a roar
    BROWN.append(_level)
_peak = max(map(abs, BROWN))
BROWN = [value / _peak for value in BROWN]


def _sample(table, t):
    return table[int(t * RATE) % len(table)]


def boom(f, t, decay):
    """An explosion's thump: a low sine that starts three octaves sharp and drops to f."""
    sweep = 18.0
    phase = TAU * f * (t + 7 * (1 - math.exp(-sweep * t)) / sweep)
    return math.exp(-decay * t) * math.sin(phase)


def crackle(f, t, decay):
    """The crack of a blast: white noise with louder sparse pops, quickly damped."""
    value = _sample(WHITE, t)
    pop = 0.8 * value if abs(value) > 0.97 else 0.0
    return (0.5 * value + pop) * math.exp(-decay * t)


def rumble(f, t, decay):
    """The roar after a big blast: low-passed noise with a soft attack."""
    return _sample(BROWN, t) * min(1.0, t / 0.03) * math.exp(-decay * t)


def fizz(f, t, decay):
    """Salt dissolving: high, thin noise (the difference of neighbouring samples) that swells."""
    i = int(t * RATE)
    hiss = WHITE[i % len(WHITE)] - WHITE[(i - 1) % len(WHITE)]
    return 0.35 * hiss * (1 - math.exp(-12 * t)) * math.exp(-decay * t)


def bubble(f, t, decay):
    """A bubble rising in water: a short sine whose pitch climbs."""
    return math.exp(-decay * t) * math.sin(TAU * f * (t + 3 * t * t))


VOICES = {'glass': glass, 'metal': metal, 'clank': clank, 'boom': boom, 'crackle': crackle,
          'rumble': rumble, 'fizz': fizz, 'bubble': bubble}


def rattle(count, seconds, seed=7):
    """Glass fragments knocking together at random, for a stirred vessel."""
    rng = random.Random(seed)
    return [(rng.uniform(0.02, seconds * 0.7), rng.uniform(1800, 3400), rng.uniform(25, 45), 'glass')
            for _ in range(count)]


def bubbles(count, seconds, seed=5):
    """Bubbles breaking at random through a fizz, for salt dissolving in water."""
    rng = random.Random(seed)
    return [(rng.uniform(0.03, seconds * 0.75), rng.uniform(600, 1500), rng.uniform(28, 45), 'bubble')
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
    # Explosions: a thump, a crack and (for the bigger ones) a roar, under the symbol's own
    # bell, so the three tiers stay distinct and grow with the blast.
    'line_burst': (0.9, [(0.0, 95, 14, 'boom'), (0.0, 0, 38, 'crackle'), (0.03, 'A5', 5, 'metal'),
                         (0.08, 'D6', 7, 'glass')], 0),
    'square_burst': (1.1, [(0.0, 70, 9, 'boom'), (0.0, 0, 22, 'crackle'), (0.0, 0, 7, 'rumble'),
                           (0.04, 'D5', 4.5, 'metal'), (0.12, 'G5', 6, 'glass')], 0),
    'element_burst': (1.8, [(0.0, 48, 5, 'boom'), (0.0, 0, 12, 'crackle'), (0.0, 0, 3.2, 'rumble'),
                            (0.12, 'C4', 3, 'metal'), (0.22, 'G4', 3.5, 'metal'), (0.34, 'C6', 5, 'glass'),
                            (0.44, 'G6', 5, 'glass'), (0.54, 'C7', 6, 'glass')], 0),
    'dissolve':  (1.0, [(0.0, 0, 2.8, 'fizz'), (0.0, 'E6', 9, 'glass')] + bubbles(10, 1.0), 0),
    'salt':      (0.25, [(0.0, 'A2', 24, 'clank'), (0.0, 0, 70, 'crackle')], 0),
    'undo':      (0.3, [(0.0, 'G5', 24, 'glass'), (0.06, 'C6', 24, 'glass')], 0.12),
    'hint':      (0.4, [(0.0, 'B6', 12, 'glass'), (0.08, 'F#7', 14, 'glass')], 0),
    'shuffle':   (0.7, rattle(9, 0.7), 0.35),
    'restart':   (1.1, [(0.0, 'G3', 3, 'metal'), (0.12, 'C4', 3, 'metal')], 0),
    'success':   (1.9, [(0.0, 'C5', 3, 'metal'), (0.12, 'E5', 3, 'metal'), (0.24, 'G5', 3, 'metal'),
                        (0.36, 'C6', 2.6, 'metal'), (0.5, 'E7', 4, 'glass'), (0.58, 'G7', 4, 'glass')], 0),
    'failure':   (1.4, [(0.0, 'E4', 3.2, 'metal'), (0.2, 'C4', 3.2, 'metal'), (0.4, 'A3', 2.6, 'clank')], 0),
    'chapter_complete': (2.6, [(0.0, 'C3', 1.8, 'metal'), (0.0, 'C5', 2.6, 'metal'), (0.15, 'E5', 2.6, 'metal'),
                               (0.3, 'G5', 2.6, 'metal'), (0.45, 'C6', 2.4, 'metal'), (0.6, 'E6', 3, 'glass'),
                               (0.75, 'G6', 3, 'glass'), (0.9, 'C7', 3.4, 'glass'), (1.15, 'E5', 2, 'metal')], 0),
    'game_over': (2.0, [(0.0, 'C3', 1.6, 'metal'), (0.0, 'G4', 2.2, 'metal'), (0.3, 'C5', 2, 'metal'),
                        (0.3, 'E5', 2.2, 'metal'), (0.45, 'G6', 4, 'glass'), (0.6, 'C7', 4, 'glass')], 0),
}


def render(seconds, notes, noise=0.0, rate=RATE):
    """Mix the notes and an optional noise tap or swell into 16-bit mono samples."""
    length = int(seconds * rate)
    mix = [0.0] * length
    for start, pitch, decay, voice in notes:
        base, sound = note(pitch), VOICES[voice]
        first = int(start * rate)
        # Every voice decays at least as fast as exp(-decay * t): stop once it is below
        # one part in 10,000 (under one step of 16-bit audio at this volume).
        last = min(length, first + int(9.2 / decay * rate))
        for offset in range(first, last):
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
