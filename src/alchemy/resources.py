"""Custom artwork overrides with packaged fallbacks."""
import logging
from importlib.resources import files
from pathlib import Path
import pygame

NAMES = ('fire', 'water', 'air', 'earth', 'sun')


def source_directory(name):
    root = Path(__file__).resolve().parents[2]
    return root / name if (root / 'src' / 'alchemy' / 'app.py').is_file() else None


def load_symbols(directory=None):
    custom_root = Path(directory) if directory else source_directory('img')
    if directory and not custom_root.is_dir():
        logging.warning('Artwork directory does not exist: %s', custom_root)
    symbols = []
    for name in NAMES:
        surface = None
        custom = custom_root / f'{name}.png' if custom_root else None
        if custom and custom.exists():
            try:
                surface = pygame.image.load(str(custom))
            except (pygame.error, OSError) as error:
                logging.warning('Cannot load %s; using bundled artwork: %s', custom, error)
        if surface is None:
            resource = files('alchemy').joinpath('assets', f'{name}.png')
            try:
                with resource.open('rb') as stream:
                    surface = pygame.image.load(stream, f'{name}.png')
            except (pygame.error, OSError) as error:
                raise RuntimeError(f'Cannot load bundled symbol {name}.png: {error}') from error
        symbols.append(pygame.transform.smoothscale(surface.convert_alpha(), (48, 48)))
    return symbols
