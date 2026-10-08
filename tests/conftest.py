"""Shared pytest setup: headless SDL drivers and `src/` on the import path.

Run everything from the repo root with `python -m pytest`. The unittest command in the
README still works for tests/test_*.py; the pytest-style edge tests live in tests/edge/.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

SRC = Path(__file__).resolve().parents[1] / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
