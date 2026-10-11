# alchemy — review and improvements

## Implementation update

The original review below is retained as historical context. The current working version fixes per-line scoring, custom-image fallback, screenshot and display errors, safe cycling hints, consistent resolve results, coordinate/volume validation, import guards, and safe artwork regeneration. It adds resizable rendering, reaction score breakdowns, explicit artwork overrides, case-insensitive sound extensions, and cross-platform installed-wheel CI. Solid blocks intentionally retain all qualifying plus bonuses; seeded restarts intentionally repeat the experiment. Version 0.1.0 has already been published; a new release needs a new version. Local scoreboards and limited-reactant difficulty remain future work.

## Mode comparison: four elements vs diagonal matches (2026-10-10)

Two experiment branches sit on top of `main` at `a180e63` ("Slow board entrances and
falling tile animations"), each one commit, neither pushed to GitHub:

- `experiment/four-elements` (`e5ab97b`): `KINDS = 4`, `NAMES` drops `sun`, orthogonal
  matching unchanged, `RULES = 'four-elements-experiment-v1'`.
- `experiment/diagonal-matches` (`0aef8ea`): five elements kept, `matched_runs()` gains
  the `(1, 1)` and `(-1, 1)` directions with corrected bounds checks,
  `RULES = 'diagonals-experiment-v1'`.

The open question was which ruleset becomes the primary "classic" mode and which becomes
an opt-in alternative.

### What was measured

Each ruleset's `board.py` was extracted into an isolated tree and played headless for 80
seeded games (seeds 0-79, 30 moves each) under two policies: a uniformly random legal move,
and a one-step greedy move maximising immediate points (tiles x 25, plus per-line
beyond-four, plus L/T/plus crossings, ignoring cascades). Move selection used a separate
`Random(10000 + seed)` so the game's own generator was never consumed. Animation timings do
not enter these numbers, so the slower-animation commit on `main` does not affect them.

| metric | main (5 el, orthogonal) | four-elements | diagonals |
| --- | --- | --- | --- |
| legal moves per turn | 2.9 | 4.5 | **5.2** |
| auto-reshuffles per 30-move game | **4.8** | 1.3 | 0.9 |
| cascade rate (chain >= 2) | 10.6% | 18.7% | **21.3%** |
| triple-cascade rate | 0.6% | 3.5% | **4.0%** |
| clear footprint, bounding-box cells (p90) | 4.2 (4) | 4.5 (5) | **11.4 (16)** |
| diagonal share of matched runs | 0% | 0% | **52%** |
| L/T/plus bonus rate per resolve (random / greedy) | 0.1% / 0.6% | **0.5% / 1.7%** | 0.3% / 0.8% |
| mean score (random / greedy) | 3929 / 4108 | 5113 / 5016 | 5301 / **5705** |
| new-board generation, mean ms (p95) | 2.3 (2.9) | 2.1 (2.3) | 6.0 (7.2) |

### Recommendation: four elements as classic, diagonals as the alternative mode

1. **The "spectacular" feel is real and it is 2.7x.** A diagonal clear disturbs a bounding
   box of 11.4 cells on average, p90 of 16, against 4.5 for either orthogonal ruleset. That
   is why it reads as a showpiece, and also why it is a poor default: a new player watching a
   quarter of the board rearrange cannot reconstruct what caused it. As a mode you opt into,
   it is the attraction.
2. **The title already teaches the four-element rules.** "The Fourfold Art", match-four, four
   classical elements. Five-with-sun breaks that rhyme, since sun is sol/gold rather than an
   element. The default mode should be the one whose name is the tutorial.
3. **Diagonals dilute the 0.1.3 shape bonuses.** 52% of matched runs in that branch are
   diagonal, and `shape_crossings()` (`src/alchemy/board.py:36`) classifies only crossings of
   horizontal and vertical runs. Half the match stream therefore can never earn an L, T, or
   plus, so the marquee mechanic goes quietest in the mode with the most activity. Four
   elements moves the other way and roughly triples the bonus rate.
4. **Either experiment fixes a real defect in current `main`.** Five elements with orthogonal
   matching only leaves 2.9 legal moves per turn and auto-rebrews the board 4.8 times per
   30-move game, about every sixth move, so players read "a fresh board has been brewed"
   constantly. Whichever ruleset becomes classic, five-elements-orthogonal should not stay as
   the shipped default.

**Evidence against this recommendation, recorded honestly:** four elements showed no greedy
advantage over random play (5016 greedy against 5113 random, and random's single best run was
higher at 11,075), while diagonals rewarded one-step lookahead by 7.6% and had the highest
ceiling at 9,600. By that proxy diagonals express skill better. The proxy is crude, since
one-step immediate-points greedy ignores cascade setup, and four elements' variance collapse
under greedy play (sd 481 against 1226) reads more like "rewards consistency" than "ignores
skill". Worth a human playtest before committing.

### Decision taken, and what shipped (2026-10-10)

Four elements became the primary mode and is named **Classic** (`classic-30`, the default).
Five-element straight-lines-only play was **retired** rather than kept as a third mode: it
was the source of the staleness this comparison measured, with only 2.9 legal swaps per turn
and 4.8 free reshuffles per 30-move game. Its recorded scores are preserved in the database
under `classic-30` with the retired `shapes-v2` rules key, labelled **legacy** in the
scoreboard and reachable with Tab. Nothing was rewritten or deleted. Current play records
under `shapes-v3`.

**Diagonal mode also gained diagonal swaps**, which the experiment branch did not have; it
had kept orthogonal-only swapping while matching in four directions. Allowing a swap with
any touching symbol transforms its move economy:

| metric | retired 5-element | Classic (4 elements) | Diagonal (diagonal swaps) |
| --- | --- | --- | --- |
| legal moves per turn | 2.9 | 4.5 | 11.2 |
| worst-case moves (p10) | 1.0 | 2.0 | 5.0 |
| auto-reshuffles per 30-move game | 4.8 | 1.29 | **0.06** |
| cascade rate | 10.6% | 18.7% | 21.8% |
| triple-cascade rate | 0.6% | 3.5% | 5.0% |
| mean score, random play | 3929 | 5113 | 5521 |

A stale board is now effectively impossible in Diagonal: 80 games produced five reshuffles
in total. The open question moves to the other end: with 11 swaps available and 5 even on
the worst turn, Diagonal may be too permissive to feel like a puzzle. If playtesting says so,
the levers are fewer moves or a higher match threshold, not fewer swap directions, which is
what makes the mode feel alive.

Ten of this section's shipping notes were implemented as described: the `Mode` dataclass in
`src/alchemy/modes.py`, mode-parameterised rules in `board.py`, `RULE_HISTORY` cycling, the
`--mode` flag and the **C** key, and per-mode scoreboard partitioning. Two deviations:
`SIZE` stayed a module constant in `board.py` because no mode varies it, and `Mode` gained a
`swaps` field, separate from `directions`, so matching and swapping can differ.

### Shipping both: put the variant in `MODE`, not `RULES`

`src/alchemy/scores.py` already separates `MODE = 'classic-30'` from `RULES = 'shapes-v2'`,
and `Scoreboard.top()` filters on both. Both branches instead overload `RULES` with the
variant name and demote the previous value into `LEGACY_RULES`. That is fine for a throwaway
experiment and wrong for a shipped mode:

- `RULES` should version the scoring *formula*, and change when point values change.
- `MODE` should name the *variant*: `classic-30`, `diagonal-30`.
- The scoreboard's Tab toggle holds exactly two keys, `RULES` and `LEGACY_RULES`
  (`src/alchemy/app.py:152`). Promoting either branch as-is silently orphans the
  `per-line-v1` history that Tab can currently reach. It needs a list of known rule keys plus
  a separate mode selector.

`KINDS` and the matching directions have to become per-mode runtime values instead of module
constants. That is the real merge cost: they are imported at module level by `app.py` (the
`COLORS` list and its `assert`), `resources.py` (`NAMES`), and `motion.py` (`SIZE`).

- `matched_runs(grid, directions=((1, 0), (0, 1)))`, with diagonal mode passing four
  directions. The diagonals branch's bounds fix (`0 <= px < SIZE and 0 <= py < SIZE`) is
  correct for both direction sets, so that diff unifies cleanly as one parameter.
- A `Mode` dataclass (`name`, `kinds`, `names`, `colors`, `directions`, `moves`, `rules_key`)
  threaded through `Game`, `matches`, `shape_crossings`, `legal_moves`, `new_grid`, and
  `refill`. `app.py` then reads colours, the window caption, and the "The practice" rule lines
  from the mode rather than from globals.
- Expose it as `--mode diagonal-30` plus a key or button. The scoreboard partitioning already
  in place does the rest.
- Keep all five PNGs packaged; four-element mode simply uses four of them.
- The `assert len(NAMES) == len(COLORS) == KINDS` at `app.py:22` becomes per-mode validation,
  and should be a raised exception rather than an `assert`, which vanishes under `python -O`.

**Re-land the experiments, do not merge the branches into each other.** Both edit the same
caption, subtitle, and `RULES` lines, so they conflict by construction. Land the mode
plumbing on `main` with only classic defined, then add each variant as a roughly 30-line mode
definition.

Both branches also had to patch test fixtures that hardcode `% 5`, and the diagonals branch
had to change `tests/test_board.py`'s baseline from `(x+y) % 5` to `(x+2*y) % 5` because
`(x+y) % 5` has constant anti-diagonals, meaning the old fixture matches everywhere once
diagonals count. Those fixtures should be derived from the mode too.

Finally, each branch prepends an experiment banner above the real README. That becomes a mode
section rather than a document header.

### Side finding: the L/T/plus bonuses are nearly unreachable

Across all three rulesets the shape bonuses fire on well under 2% of resolves: 0.1% of
resolves under random play on `main` and 0.6% under greedy, so the 0.1.3 marquee mechanic
lands roughly once every few games. Four elements helps, to 1.7% under greedy, but it is still
rare. If shapes are meant to matter, the lever is board size or fewer kinds, not larger point
values, which only make a rare event feel rarer when it finally arrives.

Reviewed commit `6185a9c` ("Add playable Pygame match-four alchemy game") on `main`, 2026-10-08. I used Python 3.12.15 and pygame 2.6.1 (SDL 2.28.4) with SDL dummy video/audio drivers.

## Summary

Alchemy is a small Pygame match-four puzzle on an 8×8 board with five alchemical symbols. You get 30 moves, cascades multiply the score, a "true plus" earns a 200-point bonus, dead boards are reshuffled automatically, and sound effects are optional drop-in files. The code is cleanly split. `board.py` holds the pure rules, `audio.py` handles optional sound, and `app.py` does rendering and input. That split made most of the game testable headless.

The rules layer is solid. Over 300 seeded games of random play, no invariant broke: the board never ended up with no legal moves, it never sat with an unresolved match, `game_over` fired exactly once, and runs were fully deterministic. The 12 existing tests pass in about 2 s under both `unittest` and `pytest`. The wheel builds, installs, and runs with its packaged fallback assets. The main problems are a scoring rule that doesn't match the README, and startup and CLI error handling: several ordinary mistakes end in a raw pygame traceback instead of a fallback or a clear message.

**Edge-case run:** 97 test cases in 3 files, plus build, install, and tool checks. **7 failed, covering 4 distinct bugs**, plus 1 latent issue I could only reproduce by forcing it. All are below.

### Where the tests live
- The edge-case tests are in `tests/edge/` (`test_board_edge.py`, `test_audio_edge.py`, `test_cli_app_edge.py`). `tests/conftest.py` puts `src/` on the import path and sets the SDL dummy video and audio drivers, so they run headless.
- Run everything from the repo root with `python -m pytest` (needs `pytest`). The README's `unittest` command still runs only the original `tests/test_*.py` files.
- Each test that fails because of a known bug below is marked `pytest.mark.xfail(strict=True, reason=...)`, so the suite stays green. When you fix a bug, its test will start passing and fail loudly as **XPASS(strict)**. **Remove that xfail marker as each bug is fixed.**
- Tests whose docstring starts with "Documents" pin current behaviour that's debatable (for example a solid 4×4 block scoring four pluses, or `resolve()` returning `None`). Update them if you change that behaviour on purpose.
- In the repo, the fuzz test uses 100 seeds and the greedy-score test uses 10 seeds to keep the suite at about 30 s. The review itself ran 300 and 40.

---

## Bugs found (most severe first)

### 1. The "beyond four" bonus also applies to separate lines cleared together (scoring vs README)
- **Reproduce:** `tests/edge/test_board_edge.py::test_reachable_two_line_swap_from_real_move` (xfail). One normal swap, `(3,0)↔(3,1)`, completes a horizontal 4 in row 0 and a separate vertical 4 in column 3.
- **Observed:** 8 tiles clear for **300** points: 8×25 = 200, plus (8−4)×25 = 100 "beyond four".
- **Expected (README):** "Each cleared symbol earns 25 points, with another 25 for each symbol beyond four." Read per line, two 4-lines are worth **200**, since neither line is longer than four. The same thing happens when unrelated lines clear in the same cascade step.
- **Where:** `src/alchemy/board.py:117-120`. `count = len(self.pending)` combines every simultaneous match into one group.
- **Fix:** Group `pending` into connected components, or into the individual runs that `matches()` finds, and compute `max(0, len(group) - 4)` per group. Keep "intersections count each tile once" by deduplicating tiles inside a component. If adding up all tiles is intended, reword the README to "for each symbol beyond four *in the whole clear*". Either way, add a test that pins the rule.
- **Severity:** Medium. The game still plays, but scores are inflated relative to the documented rules.

### 2. A corrupt, empty, or directory-typed custom image crashes startup instead of falling back
- **Reproduce:** Replace `img/fire.png` with garbage bytes, a zero-byte file, or a directory with that name, then run `python -m alchemy --smoke-test`. Tests (xfail): `test_corrupt_custom_image_falls_back`, `test_empty_custom_image_falls_back`, `test_directory_named_like_image_falls_back` in `tests/edge/test_cli_app_edge.py`.
- **Observed:** Traceback ending in `pygame.error: Unsupported image format`, exit code 1.
- **Expected:** The README tells users to replace these PNGs, and a packaged fallback already exists in `src/alchemy/assets/`. A bad custom image should log a warning and use the fallback.
- **Where:** `src/alchemy/app.py:43-45`. `custom.exists()` is true for directories, and `pygame.image.load` isn't wrapped.
- **Fix:** Use `custom.is_file()`, then `try: load(custom) except (pygame.error, OSError): logging.warning(...); load(fallback)`. Move this into a `load_symbols()` helper so it can be unit-tested. If the packaged fallback is missing too, it currently raises `FileNotFoundError` (tested). Exit with a short message naming the file.

### 3. `--screenshot` into a missing directory crashes after the window opens
- **Reproduce:** `SDL_VIDEODRIVER=dummy python -m alchemy --smoke-test --screenshot /tmp/nope/x.png` (test: `test_screenshot_into_missing_dir_gives_clean_error`, xfail)
- **Observed:** Traceback `pygame.error: Couldn't open /tmp/nope/x.png`, exit code 1. Without `--smoke-test`, the game crashes as soon as the first frame renders.
- **Expected:** An argparse-style error before pygame starts, such as `--screenshot: directory /tmp/nope does not exist`, or the directory gets created.
- **Where:** `src/alchemy/app.py:151-152`, with no validation at `app.py:25`.
- **Fix:** After `parse_args()`, check `args.screenshot.parent.is_dir()` and call `parser.error(...)` if it's missing. Wrap the save in `try/except pygame.error`.
- **Related, minor:** `--help` says "Save the rendered frame as PNG", but a path without an extension is saved as **TGA**. I checked the header bytes. `.jpg` and `.bmp` paths save in those formats. Either force PNG by appending `.png` when there's no suffix, or reword the help text.

### 4. No display or video driver gives a raw traceback
- **Reproduce:** `SDL_VIDEODRIVER=nonexistent-driver python -m alchemy` (the same thing happens on a headless box with no DISPLAY). Test: `test_no_video_device_gives_clean_error` (xfail).
- **Observed:** A multi-line traceback ending in `pygame.error: nonexistent-driver not available`.
- **Expected:** One line, for example `alchemy: cannot open a window (no display available). For headless runs use SDL_VIDEODRIVER=dummy.`, then exit code 1.
- **Where:** `src/alchemy/app.py:34` (`pygame.display.set_mode`).
- **Fix:** `try/except pygame.error as e: sys.exit(f"alchemy: cannot open window: {e}")`.

### 5. (Possible, latent) Hint crashes with `IndexError` if the board is ever dead
- **Reproduce:** Only by forcing it. `tests/edge/test_cli_app_edge.py::test_hint_on_dead_board_does_not_crash` (xfail) sets a dead grid and presses H, which raises `IndexError` at `legal_moves(...)[0]`.
- **Why "possible":** `Game` currently guarantees a legal move whenever `moves > 0` and nothing is pending, and 300 fuzzed games never broke that. A future rule change (bigger `KINDS`, special tiles, a "no reshuffle" mode) would turn this into a crash.
- **Where:** `src/alchemy/app.py:72` and `app.py:80`.
- **Fix:** Add a `Game.hint()` that returns `None` when there are no moves, then show a message instead of indexing.

### Lower-severity quirks (reproduced; design calls rather than clear bugs)
- **A solid 4×4 block scores as four "true pluses" (+800).** Every interior cell of the block meets the plus test (`board.py:44-46`), as shown in `test_solid_4x4_block_counts_as_four_pluses`. The README says "a true plus… both runs extend on both sides of the crossing", which literally holds, but a blob isn't really a plus. It can only happen through random cascades, so it's rare. Decide whether you want it, then document it or require the four neighbours *diagonal* to the crossing to differ.
- **With `--seed`, every "New game" (R or the button) deals the identical board** (`app.py:69`, `app.py:77`). That's arguably fine for reproducibility, but players will notice. Consider seeding only the first game, or deriving later seeds as `seed + n`.
- **The hint is always the first legal move in scan order** (top-left first), so pressing H again never shows anything else (`app.py:72`). Consider cycling through `legal_moves()` or picking with `game.rng`.
- **Importing `alchemy.__main__` starts the game.** There's no `if __name__ == "__main__":` guard (`__main__.py:3`). I confirmed an import launched it. This matters for tooling and doc generators.
- **`tools/draw_symbols.py` crashes if `img/` is missing.** It creates `src/alchemy/assets/` (line 23) but not `img/` (line 21): `pygame.error: Couldn't open …/img/fire.png`. It also runs at import time and silently overwrites custom art in both folders. Add `ROOT.mkdir(exist_ok=True)`, a `main()` guard, and an `--force`/confirmation option. Its output is pixel-identical to the committed PNGs, so it is deterministic.

---

## Edge cases tested that passed
- **Matching:** grids full of `None` or a single symbol; runs of exactly 4 against the right and bottom edges; diagonals ignored; `None` breaking a run; unicode string symbols; short grids raise `IndexError` (they don't hang).
- **Plus detection:** a T on the border is not a plus; one long row with two vertical crossings gives 2 pluses; a 5×5 plus scores exactly 550 with `match` and `plus` events.
- **Swaps:** out-of-range (−1, 8), self-swap, diagonal, and distance-2 swaps are all rejected without changing the board or spending a move. Swaps are rejected while a match is pending and when `moves` is 0 or negative. `legal_moves` never mutates the grid and every move it returns really matches. A dead board returns `[]`.
- **Refill:** a full-board refill gives valid kinds; an empty or out-of-range cleared set is a no-op; gravity keeps order (existing test).
- **Seeds:** 0, −1, 2²⁰⁰, `'abc'`, unicode text, float, and bytes are all deterministic within a game. `--seed 42` gives byte-identical screenshots under `PYTHONHASHSEED` 0, 1, and 12345. `seed=None` varies. An unhashable seed raises `TypeError`.
- **Fuzzing:** 300 seeds × 30 random legal moves held every invariant, including exactly one `game_over`. A dead-board reshuffle always gives a board with no matches and at least one legal move. No reshuffle happens on the final move.
- **Performance:** `new_grid` takes about 2.7 ms and `legal_moves` about 2.3 ms. A headless frame takes about 1.5 ms. The best greedy-play score across 40 seeds was 7,600, well under the roughly 100,000 where the 48-pt score would run into the "MOVES" column.
- **Audio:** missing or file-typed `--sound-dir`; unicode and space-containing paths; all 10 events loading; WAV-over-OGG priority; a corrupt WAV falling back to OGG; empty and zero-frame files; a directory named `match.wav`; volume clamped to [0, 1]; muted start; play and toggle after the mixer shuts down; unknown or `None` events; 100 overlapping plays; mixer init failing.
- **CLI (non-TTY, stdin=/dev/null):** `--volume abc/-0.1/1.01/nan/inf`, a missing value, `--seed abc/1.5`, and unknown flags all exit 2 with usage and no traceback. Unusual but valid arguments run with no stdout noise. `--help` works without a display. `.png/.jpg/.bmp` screenshots and unicode screenshot names work. The game runs from any working directory.
- **Assets:** missing single custom image, missing `img/` dir, 1×1 images, 4000×300 non-square images, 8-bit palette images, and a JPEG named `.png` all render.
- **Scripted headless game loop** (events injected into `app.main()`): a full 30-move game played by clicking; after game over, H, clicks, right-clicks, out-of-board clicks, and M/M all do nothing harmful; R during a cascade and the New-game button reset cleanly; clicks on tile gaps and board edges are handled.
- **Packaging:** `uv build` gives a wheel containing `assets/*.png`. The installed (non-editable) wheel runs `alchemy --smoke-test` from `/`, and its screenshot is identical to the source run. `uv lock --check` is clean.

## Code quality and structure
- **Rules and UI duplicate constants.** `app.py:85` hard-codes `8` (use `SIZE`), `app.py:144` hard-codes `560` (use `SIZE*TILE`), and `NAMES`/`COLORS` must stay at the same length as `board.KINDS`. Derive these from one place, or assert `len(NAMES) == KINDS` at import.
- **`Game.resolve()` returns `None` when nothing is pending but a list otherwise** (`board.py:114-115`). Return `[]` so callers can always iterate.
- **`Game.attempt()` accepts non-int coordinates.** They pass the range check, then `swap()` raises `TypeError`. Validate `isinstance(v, int)` or coerce.
- **`Audio(volume=nan)` plays at full volume.** `min`/`max` don't clamp NaN, though the CLI already rejects it. `Audio(volume='0.5')` raises `TypeError` outside the `try`. Coerce with `float()` and reject non-finite values in `Audio`.
- **`app.main()` is one 135-line function.** Split it into `parse_args()`, `load_symbols()`, `handle_event()`, `draw()`, and a small `UIState` (selected, hint, next_resolve). That makes input handling unit-testable without patching `pygame.event.get`.
- **The render loop allocates every frame:** two `render()` calls per button label (`app.py:139`), a new `Surface` per pending tile (`app.py:121`), and the game-over shade (`app.py:144`). Cache them. It's cheap now (about 1.5 ms per frame), but easy to fix.
- **Asset and sound paths use `Path(__file__).parents[2]`** (`app.py:38`, `audio.py:21`). Installed from a wheel, that points at `…/lib/python3.12/img` and `…/sounds`. It's harmless today but surprising. Use `importlib.resources` for packaged assets, plus an explicit `--assets-dir` or env var for custom art.
- **Silent failures:** a nonexistent `--sound-dir` gives no warning (a user typo goes unnoticed), and uppercase extensions like `match.WAV` aren't found. Log one info line listing which effects loaded.
- **The game loop runs at 60 fps even when idle.** Consider a lower idle tick, or `pygame.event.wait` when nothing is animating, to save battery.

## Testing gaps (specific tests to add)
1. **Scoring table:** one test per README rule, including two separate 4-lines, 4+5 lines, an L shape, a T shape, a plus with long arms, two pluses on one line, and cascade ×2 and ×3. Pin bug 1 here.
2. **Asset loading:** corrupt, empty, or directory custom images fall back. Missing packaged assets give a clean error.
3. **CLI errors:** `--screenshot` into a missing directory, and no video driver. Assert no `Traceback` in stderr (now covered by the xfail tests in `tests/edge/test_cli_app_edge.py`).
4. **Property and fuzz test** (the existing `test_full_games_are_playable` covers only 8 seeds and always the first move): random moves across hundreds of seeds, checking invariants after each `resolve()`. Hypothesis would fit well here.
5. **Determinism:** a full game replay with a fixed seed and fixed move list gives a known final score and grid. That catches accidental RNG-order changes.
6. **UI logic:** once input handling is extracted, test selection toggling, non-adjacent re-selection, ignored clicks while pending or after game over, hint clearing, and restart.
7. **Packaging smoke test in CI:** build the wheel, install it in a clean venv, and run `alchemy --smoke-test`.
8. **`tools/draw_symbols.py`:** it runs in a temp copy without `img/` and gives pixel-identical output.

## Packaging, docs, and UX
- **PyPI name: resolved.** `alchemy` on PyPI belongs to catalyst-team (an unrelated experiment-logging library, versions 20.4 and 20.5), so the distribution name is now `alchemy-game`, which was free on PyPI as of 2026-10-08. PyPI does not reserve names, so it is only claimed once a first release is uploaded. The `alchemy` import and command names are unchanged.
- **License: resolved.** The project is MIT-licensed. `LICENSE` reads "Copyright (c) 2026 Andrew Davidson". `pyproject.toml` uses the PEP 639 fields `license = "MIT"` and `license-files = ["LICENSE"]`, which uv_build 0.12.23 supports: the built wheel has `License-Expression: MIT` and ships `LICENSE`. The license covers the code and the generated symbol art.
- **`img/AoA_symbols.pdf`** is a third-party-looking reference (an Adobe InDesign 2015 export). The README already says rights haven't been reviewed. Since the repo is public, consider removing it, or confirm you're allowed to redistribute it.
- **CI: resolved.** `.github/workflows/ci.yml` runs the full pytest suite and a headless smoke test on Ubuntu with Python 3.12 and 3.13, on every push and PR to `main`. Plain `pytest` already works without `PYTHONPATH`, because `tests/conftest.py` adds `src/`. Still optional: a `[dependency-groups] dev = ["pytest"]` entry, so `--with pytest` isn't needed.
- **The sdist leaves out `tests/`, `tools/`, and `sounds/README.md`.** Include tests if you want downstream packagers to run them.
- **README:** document the exact scoring formula once bug 1 is settled, with a worked example. Say that R with `--seed` repeats the same board. Mention that the window is a fixed 1040×780 (a resizable or scaled window would help on small laptop screens).
- **UX ideas:** cycle through hints, animate falling tiles, add keyboard or arrow-key play for accessibility, and show a "no more hints" or "game over" message when H is pressed after game over.

## Next steps (in order)
1. Decide the "beyond four" rule. Fix `resolve()` or the README to match, and add scoring tests.
2. Add safe image loading with fallback (`is_file()` and `try/except`) and a helper that can be tested.
3. Validate `--screenshot` early, and catch `set_mode` failures, so no user-facing tracebacks remain.
4. Add `Game.hint()` and make `resolve()` always return a list.
   - After each of fixes 1–4, remove the matching `xfail` marker in `tests/edge/`.
5. ~~Add CI and a LICENSE~~ (done). Still to do: review whether to keep `AoA_symbols.pdf` in the public repo. It isn't shipped in the sdist or wheel. Optionally add a wheel-install test to CI.
6. Release 0.1.0 as `alchemy-game` once you've done the one-time PyPI setup under "Releasing" below. The PyPI name item is resolved: `alchemy` belongs to catalyst-team.
7. Refactor `app.main()` into testable pieces, then add UI-logic tests.

## Releasing

Packaging is ready for 0.1.0. The distribution name is `alchemy-game`; the import and the `alchemy` command are unchanged. Releases go out through `.github/workflows/publish.yml` using PyPI **Trusted Publishing** (OIDC), so no API token is stored anywhere.

**One-time setup (do this yourself, in a browser):**
1. Create a PyPI account at https://pypi.org/account/register/ and turn on two-factor authentication. PyPI requires 2FA to publish.
2. Go to https://pypi.org/manage/account/publishing/ and, under "Add a new pending publisher", choose the GitHub tab and enter:
   - PyPI Project Name: `alchemy-game`
   - Owner: `wulfalpha`
   - Repository name: `alchemy`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

   A pending publisher doesn't reserve the name. `alchemy-game` is claimed only when the first upload succeeds. It was free on PyPI and TestPyPI as of 2026-10-08.
3. Optional: in the GitHub repo, go to Settings → Environments → New environment and create `pypi`. You can add yourself as a required reviewer so each publish waits for your approval. If you skip this, the workflow creates the environment automatically the first time it runs.
4. Optional dry run on TestPyPI: create an account at https://test.pypi.org (it's separate from PyPI) and add the same pending publisher at https://test.pypi.org/manage/account/publishing/. The workflow only targets real PyPI. To publish to TestPyPI, add a second job (or a temporary edit) with `repository-url: https://test.pypi.org/legacy/` on `pypa/gh-action-pypi-publish` and a matching environment name, such as `testpypi`.

**Each release:**
1. Bump `version` in `pyproject.toml` if needed (it's `0.1.0` now) and commit to `main`. Make sure CI is green.
2. Tag and push: `git tag v0.1.0 && git push origin v0.1.0`
3. The workflow runs the tests, checks that the tag matches the project version, builds the sdist and wheel with `uv build --no-sources`, and publishes them. Watch it under the repo's Actions tab.

**Notes:**
- PyPI never lets you re-upload the same version. If something is wrong, bump the version and tag again.
- uv_build 0.12+ always puts a `pyproject.toml.orig` in the sdist, next to a TOML-1.0-normalized `pyproject.toml`. That's expected backend behaviour (astral-sh/uv#18741), not a stray file.

## Adventure roadmap: finite-reactant experiments (2026-10-10)

### Agreed direction

- Classic 30 becomes the four-element game; diagonal matching is optional through
  the mode work currently being refactored. Adventure is a separate mode, not a
  change to Classic's resource or turn rules.
- Adventure is about **completing experiments with a limited kit**, not merely
  surviving for the highest score. The board is the reaction vessel; matching
  consumes the reactants in that vessel.
- Finish the current mode refactor before implementing Adventure. This section is
  a design handoff, not a request to modify the in-progress refactor.

### Proposed first playable experiment

The following mechanics and numbers are a starting proposal for playtesting,
not settled balance decisions.

1. Use fire, water, air, and earth, an 8x8 vessel, orthogonal swaps, and matches of
   four or more. Start Adventure without diagonal matching to establish a baseline.
2. Start with a full, stable, playable board and a separate reserve for each
   element. Try **20 units of each element in reserve**, in addition to the
   initial board. Count the initial board as part of the supplied kit, not as
   material created during play. Its exact composition should be reproducible
   for each experiment/seed.
3. Clear matched tiles, let survivors fall, then draw replacement tiles from the
   remaining reserves. Each replacement spends exactly one unit of its own
   element. Do not also charge an inventory fee for clearing the same tile.
4. Sample without replacement from the remaining inventory, weighted by how many
   units of each element remain. An exhausted element cannot be drawn. Material
   already on the board remains usable even when its bottle is empty.
5. With no reserve left, stop refilling and leave gaps above the surviving tiles.
   Empty cells are not reactants and cannot be swapped with a tile. The player
   may continue making legal reactions with the material still on the board.
6. Remove the 30-move limit. Invalid swaps still spend no material. The objective
   and remaining material, rather than a countdown, determine the outcome.
7. Begin with one target-score experiment; choose its target after measuring the
   achievable range. Later experiments can require specified amounts of elements
   to be reacted, or combinations of objectives. Avoid mandatory rare shapes in
   the first experiment.

For example, clearing four fire tiles consumes four fire already in the vessel.
If the refill draws two water, one earth, and one air, those are the reserves that
lose units; fire is not charged a second time. This distinction needs to be clear
in the tutorial and inventory display.

### Conservation, completion, and blocked boards

- Without recovery, `tiles on board + units in reserve` decreases by the number
  of unique tiles cleared. Refill only transfers material from bottles to vessel.
  Intersections never consume or count a tile twice.
- Resolve the full cascade before evaluating the experiment outcome. Objective
  success takes precedence over exhaustion. Empty reserves alone do not end a
  run while legal reactions remain on the board.
- Classic's free newly generated board must not be reused for Adventure: it would
  introduce free material. Proposed first recovery rule: a bounded automatic
  reshuffle of existing tiles only, preserving tile counts, reserves, and empty
  cell count. Require a stable board with a legal move and compact its columns.
  If no valid layout is found within the attempt limit, end with a clear
  "Experiment stalled" result. The limit must be explicit; do not claim the
  layout is mathematically impossible merely because the search ran out.
- Dead-board handling is still a design decision to playtest. Alternatives include
  a limited stir tool or immediate failure; neither should be silently added.
- Initial-board generation and rejected reshuffle candidates must not spend
  reserves or award objective progress. Hints and animations must not consume
  the gameplay random sequence.

### Recovery/decay: second phase, not the baseline

First test finite reserves **without refunds**. Then evaluate selective material
recovery as a reward for deliberate reactions:

| Reaction | Candidate recovery into its element's reserve |
| --- | --- |
| Four in a line | None |
| Five or more in a line | One unit |
| L, T, or plus | Two units |

Before enabling this, define overlap handling: do not blindly stack recovery for
all runs and crossings in a dense block. Total recovery must be strictly less
than the number of tiles consumed by that reaction. Cascades multiply score,
not recovered units. Specify whether recovery happens before that clear's refill
(proposed) so inventory accounting and seeded replays are unambiguous.

Call this recovered material in the UI; automatic timed decay is not part of the
first prototype. Refund amounts, reserve capacity, and interaction with future
objectives remain open questions.

### Presentation and progress

- Show the experiment's objective and progress alongside four labeled reserve
  bottles/counters. Clearly distinguish reserves from tiles already in play.
- Explain why replacement elements can differ from those consumed, and why an
  empty bottle does not make its remaining board tiles unusable.
- On success/failure, show objective progress, material used/remaining, and score.
  Start with one replayable experiment, not a campaign map or unlock economy.
- Store Adventure results separately from Classic. Partition comparable results
  by experiment ID, experiment revision (kit/objective changes), matching variant,
  scoring rules, and seed policy. Do not relabel existing Classic history.
- Keep definitions data-driven: objective, initial kit/board policy, available
  elements, refill policy, and blocked-board policy belong to the experiment.
  Reuse the refactored mode interface once it is stable; avoid another parallel
  set of global element counts or hardcoded rendering assumptions.

### Implementation sequence and acceptance checks

1. Land and verify the Classic/optional-diagonal refactor independently.
2. Add pure inventory/refill rules and one fixed-seed experiment, without refunds.
3. Add objective evaluation, finite-material blocked-board handling, and UI counters.
4. Playtest reserve size and objective difficulty; only then consider recovery.
5. Add experiment persistence and additional objectives after the core loop is fun.

Test nonnegative inventories, weighted draws excluding exhausted elements,
conservation across intersections/cascades/refills, partial refills, gravity with
empty cells, no tile creation by reshuffling, bounded dead-board handling, success
on the final available reaction, and exactly one completion result. Replays must
remain deterministic; Classic's move limit and refill behavior must stay unchanged.

Track completion rate, reserves left at completion, depletion order, stalled-board
frequency, and intentional versus accidental progress. In particular, watch
whether an exhausted element makes the board easier by reducing variety. Use
playtesting to decide whether that late-experiment rush is desirable before
adding a compensating penalty.
