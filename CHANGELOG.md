# Changelog

## Unreleased

### Classic
- Add **unstable symbols**. Exactly five in a row leaves a **Line** symbol, six or more
  in a row a **Square**, and an L, T, or plus shape an **Element**. Matching one
  detonates it: a Line clears its row or column in the direction of that match, a Square
  the 3×3 block around it, and an Element every symbol of its element on the board.
  Each extra tile cleared scores 50, times the cascade number, and caught unstable
  symbols detonate in turn. The board highlights the full blast before it clears.
- Classic scores now save under the `unstable-v1` rules. Earlier Classic scores stay
  in a **Classic / before unstable symbols** scoreboard category (press **Tab**).
- New built-in tones and optional sound files: `unstable`, `line_burst`,
  `square_burst`, and `element_burst`.
- Diagonal and Adventure are unchanged.

## 0.1.8

### Adventure
- Add Easy (8 stirs), Medium (5), and Hard (3) difficulties, available through
  the C mode cycle or `--mode adventure-8`, `adventure-5`, and `adventure-3`.
  Each has a remaining-stirs counter and its own efficiency scoreboard.
- Using the final stir permits continued play. A later blocked board ends the
  run if no stirs remain; reaching the target after the full cascade takes priority.
  Unlimited Adventure retains its existing rules and records.
- Award Bronze for winning, Silver with at least 30 material left, and Gold with
  at least 45. Medal goals appear by the material counter; awards appear on
  completion and saved wins with known material statistics. Rankings are unchanged.

### Development
- Add a reproducible Adventure calibration tool and results from 960 simulated
  runs to document the initial medal thresholds.
- Reconcile historical design reviews with implemented features and remaining work.

## 0.1.7

### Install
- **The game now depends on [pygame-ce](https://pyga.me/)** (2.5.8+) instead of pygame. pygame-ce publishes wheels for Python 3.12 through 3.15, so `pip install alchemy-game` now works on Python 3.14 and 3.15. **Upgrading with `pip install -U alchemy-game` just works:** pygame-ce is installed and takes over `import pygame`, while the old pygame stays listed beside it. To tidy up, run `pip uninstall pygame` **and then** `pip install --force-reinstall pygame-ce`. The two packages share files, so uninstalling pygame alone leaves pygame-ce broken (`module 'pygame' has no attribute 'Rect'`) until it is reinstalled.

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
