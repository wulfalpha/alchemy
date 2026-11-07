# Changelog

## Unreleased

### Campaign
- **New Campaign mode** (`--mode campaign`, or **C**): hand-designed Adventure
  experiments, one per stage of the Great Work, unlocked in order. Winning a stage
  opens the next; progress is saved locally. **E** switches between open stages.
- **Stage 1, Nigredo: The Dry Flask.** Only 8 water in reserve. Reach 3,500 points with
  up to 8 stirs; Silver at 30 material left, Gold at 40.
- **Stage 2, Albedo: Purification.** Win by removing every earth tile from the board
  and reserves (12 earth in reserve). The board starts with an earth Element symbol:
  save its blast until the earth reserve is spent. 8 stirs; Silver 30, Gold 40.
- **Stage 3, Citrinitas: The Golden Shape.** Win by detonating 3 unstable symbols of
  any kind, with reserves of 12 of each element. 8 stirs; Silver 40, Gold 50.
- Campaign experiments can have goals other than points; the sidebar and end screen
  show the goal and your progress.
- **Progression.** The three stages form Chapter 1: The Great Work. Winning a stage
  shows **Stage complete** and **Enter** (or a click) begins the next; the last stage
  shows **Chapter 1 complete** with your best medal per stage. The header shows a dot
  per stage in its best medal's colour. **E** replays any open stage.

## 0.1.10

### Classic
- **Unused unstable symbols pay out at the end.** Symbols still on the board when the
  game ends, and symbols banked when a dead board was replaced, each add a flat bonus:
  Line +100, Square +150, Element +200 (not multiplied by cascades). The bank's value
  appears under the moves counter, and the completion screen shows the payout.
- Classic scores now save under the `unstable-v2` rules. 0.1.9 scores stay in a
  **Classic / without unused-symbol bonus** scoreboard category (press **Tab**).

### Adventure
- **Unstable symbols come to Adventure** (Easy, Medium, Hard, and unlimited). A stir
  carries each one to a tile of its own element, so none are lost. Detonated tiles are
  consumed and pay 50 points each, so a well-timed blast helps your medal. A newly
  formed symbol keeps its tile. There is no bank or end bonus: unused symbols already
  count as material left, and the win screen notes how many were left unspent.
- **Medals are raised to Silver 40 and Gold 50** for the new revisions, because unstable
  symbols make efficient play much stronger. Wins from earlier revisions keep their
  original thresholds and medals.
- New experiment revisions `adventure-first-v3`, `adventure-3-v2`, `adventure-5-v2`, and
  `adventure-8-v2`. Earlier scores stay one **Tab** away under "before unstable symbols".

### Development
- `tools/measure_adventure.py` understands unstable symbols and gains `--before` to
  measure the released revisions. Results are in `docs/medal_calibration_unstable.json`.

## 0.1.9

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
