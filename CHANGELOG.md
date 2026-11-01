# Changelog

## 0.1.7

### Install
- **The game now depends on [pygame-ce](https://pyga.me/)** (2.5.8+) instead of pygame. pygame-ce publishes wheels for Python 3.12 through 3.15, so `pip install alchemy-game` now works on Python 3.14 and 3.15. Both packages provide `import pygame` and cannot share an environment: if you installed alchemy-game next to the original `pygame`, run `pip uninstall pygame` first, or install with `pipx install alchemy-game` / `uv tool install alchemy-game`.

### Sound
- **Every event now has a sound out of the box.** Built-in metal and glass tones (bells, clanks, clinking vials, a stirred vessel) are synthesised at startup. Drop-in WAV/OGG files still take priority, one event at a time; `--no-tones` plays only your files.

### Look
- **Bundled fonts**, so the game looks the same on every platform: Cormorant Garamond for headings, Cormorant Infant for the title and large numbers, and Source Sans 3 for interface text (all SIL Open Font License). Previously macOS and Windows fell back to Arial.

### Controls
- **Keyboard play.** Press an arrow key to show a cursor, move it with the arrows, and press Enter or Space where you would click. Diagonal swaps work the same way.
- **Esc clears a selection** before it quits the game.
- **R, New game, and C ask before abandoning a game in progress.** Press the same key or button again to confirm; anything else keeps playing. Untouched and finished games restart immediately.

### Adventure
- **Adventure scores rank by efficiency:** most material left, then fewest swaps, then points. Every win clears the same target, so points alone barely separated them. The scoreboard gains a Material Left column.
- **`--mode adventure`** is the new launch name. The old `--mode adventure-first-v1` still works. Saved scores are unaffected.

### Customising
- `img/` in a source checkout now holds only your replacement symbols (like `sounds/`); the default artwork lives once, inside the package.

### Development
- `app.py` is split into a `Session` class (input, timing, scoring) and `render.py` (drawing, with per-mode views).
- pytest and ruff are pinned in a `dev` dependency group, and CI lints with ruff and tests Python 3.12 through 3.15 on Linux, macOS, and Windows.
- Removed unused board code and repeated work during scoring and sound loading. Design notes moved to `docs/design_notes.md`.

Earlier releases are described in the git history and `docs/design_notes.md`.
