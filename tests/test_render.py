"""Bundled typography (SDL dummy drivers set in tests/conftest.py)."""
from importlib.resources import files
from unittest.mock import patch

import pygame
import pytest

from alchemy import render


@pytest.fixture(autouse=True)
def fonts():
    pygame.font.init()
    yield


def test_every_layout_size_uses_a_bundled_font_with_its_license():
    fonts = files('alchemy').joinpath('assets', 'fonts')
    for name, _ in render.FONTS.values():
        assert fonts.joinpath(name).is_file()
    assert fonts.joinpath('Cormorant-OFL.txt').is_file()
    assert fonts.joinpath('SourceSans3-OFL.md').is_file()


def test_canvas_loads_bundled_fonts_without_warnings(caplog):
    canvas = render.Canvas()
    assert set(canvas.fonts) == set(render.FONTS)
    assert not caplog.records
    # Larger layout sizes stay larger after the switch of typeface.
    heights = [canvas.fonts[size].get_height() for size in sorted(canvas.fonts)]
    assert heights == sorted(heights)


def test_large_numerals_are_lining_so_zero_is_not_an_o():
    """Old-style figures make 0 as short as o; the numeral font must not."""
    font = render.Canvas().fonts[48]
    zero = font.render('0', True, (255, 255, 255)).get_bounding_rect()
    letter = font.render('o', True, (255, 255, 255)).get_bounding_rect()
    assert zero.height > letter.height * 1.3


def test_missing_bundled_font_falls_back_to_a_system_font(caplog):
    with patch.object(render, 'FONTS', {14: ('missing.ttf', 15)}):
        canvas = render.Canvas()
    assert 'Cannot load bundled font missing.ttf' in caplog.text
    canvas.text('still renders', (0, 0), 14)
