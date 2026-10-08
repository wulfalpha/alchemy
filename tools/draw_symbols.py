"""Create original geometric renditions of traditional alchemical signs."""
import os
from pathlib import Path
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

ROOT = Path(__file__).resolve().parents[1] / 'img'
INK = (246, 230, 183)
for name in ('fire', 'water', 'air', 'earth', 'sun'):
    canvas = pygame.Surface((128, 128), pygame.SRCALPHA)
    if name == 'sun':
        pygame.draw.circle(canvas, INK, (64, 64), 36, 6)
        pygame.draw.circle(canvas, INK, (64, 64), 9)
    else:
        points = [(64, 25), (24, 99), (104, 99)]
        if name in ('water', 'earth'):
            points = [(x, 128-y) for x, y in points]
        pygame.draw.lines(canvas, INK, True, points, 6)
        if name in ('air', 'earth'):
            pygame.draw.line(canvas, INK, (30, 68), (98, 68), 6)
    pygame.image.save(canvas, str(ROOT / f'{name}.png'))
    packaged = ROOT.parent / 'src' / 'alchemy' / 'assets'
    packaged.mkdir(exist_ok=True)
    pygame.image.save(canvas, str(packaged / f'{name}.png'))
