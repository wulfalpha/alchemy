# Alchemy

A Pygame match-four puzzle with independently drawn alchemical symbols and a quiet laboratory aesthetic.

## Install

With Python 3.12+:

```sh
pip install alchemy-game
```

The game uses [pygame-ce](https://pyga.me/), the community edition of pygame, which publishes wheels for Python 3.12 through 3.15. Both packages provide `import pygame` and share files. Upgrading from 0.1.6 or earlier with `pip install -U alchemy-game` works as is; if you then remove the old package with `pip uninstall pygame`, follow it with `pip install --force-reinstall pygame-ce`.

Or as a standalone tool (no project venv needed):

```sh
pipx install alchemy-game
# or: uv tool install alchemy-game
```

Then run:

```sh
alchemy
```

## Play

From a clone of this repository, with [uv](https://docs.astral.sh/uv/):

```sh
uv run alchemy
```

Or install into your Python environment with `python -m pip install -e .`, then run `alchemy`.

- Click a symbol, then an adjacent symbol to swap them. To play from the keyboard, press an arrow key to show a cursor, move it with the arrows, and press **Enter** or **Space** where you would click. **Esc** clears a selection before it quits.
- Match **four or more** identical symbols horizontally or vertically. Diagonals and groups without a four-symbol line do not clear.
- Valid swaps use one of your 30 moves. Invalid swaps are reversed for free.
- Cleared tiles refill from above; further matches produce cascades.
- Each cleared symbol earns 25 points, with another 25 for each symbol beyond four **in each horizontal or vertical matched line**. A maximal line is scored only once. The total is multiplied by the cascade number. Intersections count each tile once. A true plus adds **200 points per crossing**, before the cascade multiplier: both horizontal and vertical runs must be 4+ symbols and extend on both sides of the crossing. T and L shapes earn their own bonuses, described below.
- In **Classic**, five or more in a row or an L, T, or plus shape leaves behind an **unstable symbol**. Match it later to detonate it for extra clears and points; see [Unstable symbols](#unstable-symbols-classic).
- **H** or **Hint** highlights a valid swap, without a penalty.
- **R** or **New game** restarts. **C** switches mode. **Esc** quits. Once you have made a swap, R and C ask first: press the same key (or button) again to abandon the game, or anything else to keep playing.
- Boards with no valid swaps are replaced automatically for free; the score and remaining moves carry over.

## Game modes

Six modes are available. Press **C** to switch, or start in one with
`alchemy --mode <key>`. Switching begins a new experiment, and each mode keeps its own
high-score ranking.

| Key | Mode | Symbols | Swaps | Matches run |
| --- | --- | --- | --- | --- |
| `classic-30` | Classic (default) | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `adventure` | Adventure | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `adventure-3` | Adventure Hard (3 stirs) | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `adventure-5` | Adventure Medium (5 stirs) | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `adventure-8` | Adventure Easy (8 stirs) | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `diagonal-30` | Diagonal | the four elements plus sun | any touching symbol, diagonals included | rows, columns, and both diagonals |

**Classic** is the primary mode. Four elements for a match-four game keeps about 4.5 legal
swaps available per turn. **Diagonal** adds the sun as a fifth element but lets you swap
and match in every direction, which keeps roughly 11 swaps available and means a dead
board is almost never dealt. A diagonal line earns the same per-symbol and long-line
points as a straight one, but only horizontal and vertical runs form L, T, and plus
crossings.

Classic and Diagonal are 8x8 with 30 moves. They share the same base scoring formula; Classic
adds unstable symbols, described below, so the two modes have separate scoring-rule versions. Modes are defined as data in `src/alchemy/modes.py`; adding one is
a `Mode(...)` entry in that file's registry for another 30-move variant.

### Adventure: First Transmutation

Start with `uv run alchemy --mode adventure`, or press **C** twice from
Classic. Reach **3,500 points** using the initial 64 tiles and **20 replacement
reactants of each element**. There is no move limit. Matching consumes tiles;
replacement tiles are drawn from the remaining reserves, with no refunds.
When reserves run out, empty spaces remain and cannot be swapped.

The complete cascade scores before success is checked. If no swaps remain,
the game tries up to 200 rearrangements of the existing material. No new tiles
are created by stirring. If random stirring fails with at most 16 tiles, a bounded
constructive search tries arranging them around a legal swap. If neither succeeds,
the experiment stalls; **R** retries. The ending distinguishes insufficient matching
material from an unsuccessful layout search and shows the points shortfall.
The sidebar shows your target, reserves, material remaining (board tiles plus
reserves), and material used. A notice explains when reserves run out. Both
successful and stalled experiments show points, reactants consumed, and successful
swaps and stirs; **R** retries the same experiment. The sidebar also shows points
still needed and the stir count.

This first experiment defaults to seed **42** so retries repeat the same kit and
random sequence. Use `--seed` for other starting conditions. Successful experiments
save locally under their own experiment revision and seed; stalled and abandoned
attempts do not enter the leaderboard. New results include material left, swaps,
and stirs. Because every win clears the same target, Adventure ranks by
efficiency rather than points: most material left, then fewest swaps, with points
breaking any remaining tie. Earlier wins saved without these statistics rank after
those with them. The current revision, with unstable symbols, is `adventure-first-v3`. **Tab** in
Adventure scores shows earlier revisions separately: `adventure-first-v2` (before
unstable symbols) and the original `adventure-first-v1`, with unavailable
efficiency statistics clearly labeled. The earlier launch name
`--mode adventure-first-v1` still works. The initial target is for playtesting;
campaign progression and reactant recovery are future work.

### Adventure difficulty

Choose a difficulty by its automatic stir allowance:

- **Easy — 8 stirs:** `uv run alchemy --mode adventure-8`
- **Medium — 5 stirs:** `uv run alchemy --mode adventure-5`
- **Hard — 3 stirs:** `uv run alchemy --mode adventure-3`

All appear when cycling modes with **C**. The starting kit, seed 42, 3,500-point target, and scoring
are identical to unlimited Adventure; the sidebar shows stirs left.

Using the final stir does not end the run: keep playing until you win, run out of
matching material, or need another stir with none left. The full cascade finishes
before the result is checked, and reaching the target takes priority. Failed layout
searches still end the experiment without consuming a successful stir.

Each variant has separate efficiency-ranked scores (`adventure-3-v2`,
`adventure-5-v2`, and `adventure-8-v2`, with unstable symbols). Scores from before
unstable symbols (`-v1`) are one **Tab** away. **R** retries the same variant with its full stir allowance.
These difficulty names were selected after initial playtesting. The existing
launch names and score partitions are unchanged.
The original `adventure` mode keeps unlimited free stirs.

### Unstable symbols in Adventure

Adventure uses the same [unstable symbols](#unstable-symbols-classic) as Classic, with
two differences that follow from finite material:

- **A stir keeps them.** Stirring rearranges the same material, so each unstable symbol
  moves with the vessel and lands on a tile of its own element. Nothing is banked, and
  there is no end-of-game bonus: a symbol you never use is still a tile, and already
  counts as material left. The win screen notes how many were left unspent.
- **Blasts spend material.** Every tile a detonation clears is consumed like any other.
  Each pays 50 points, more than the roughly 35 points per tile a Gold run can afford, so a
  well-timed detonation helps your medal, while a careless one wastes reactants. A newly
  formed unstable symbol keeps its tile, so forming one costs no material.

### Adventure efficiency medals

Reach the 3,500-point target to earn a medal based on **material left after the
entire final cascade** (board tiles plus reserves):

| Medal | Material left on a successful run |
| --- | --- |
| Bronze | 0–39 |
| Silver | 40–49 |
| Gold | 50 or more |

These thresholds apply to Easy, Medium, Hard, and unlimited Adventure. They were
raised with unstable symbols, which make efficient play much stronger; wins from
earlier revisions keep their original thresholds (Silver 30, Gold 45) and medals. Stirs and
swaps do not change the medal; each difficulty keeps its separate ranking.
The material counter shows the Silver and Gold goals, and wins show their medal
on the completion screen and local scoreboard. Stalled or unfinished runs earn
no medal. Existing saved wins with material statistics also display medals; older
wins without those statistics remain ungraded. Ranking and saved score values
are unchanged. The thresholds are informed by automated runs and remain subject to human
playtesting; see [the calibration notes](docs/medal_calibration.md).

Classic scores from earlier scoring rules stay in their own categories on the scoreboard:
**Classic / without unused-symbol bonus** (0.1.9, rules `unstable-v1`) and **Classic / before
unstable symbols** (rules `shapes-v3`). Press **Tab** to reach them.

Earlier five-element, straight-lines-only play is retired. Scores set under those rules are
kept and shown as **legacy** scores: open the scoreboard with **L** and press **Tab** to
cycle through current, legacy, and experimental score categories. Both experimental
branches remain accessible under their original mode/rules keys. The historical
diagonal experiment is labeled "straight swaps" to distinguish it from the new
Diagonal mode. Seeded and unseeded results remain separate. Nothing is rewritten or deleted.

## Sounds

Every event has a built-in metal or glass tone (bells, clanks, clinking vials), synthesised at startup, so the game has sound straight after `pip install`. To replace any of them, drop WAV or OGG effects into `sounds/` (or a folder given with `--sound-dir`) using the filenames in [sounds/README.md](https://github.com/wulfalpha/alchemy/blob/main/sounds/README.md), then restart. A file always takes priority over its tone, so you can replace them one at a time. Press **M** to mute, use `--volume 0.4` to adjust volume, or `--no-tones` to hear only your own files. Missing audio files or devices do not prevent play.

## Artwork

The symbols were drawn with the Getty Research Institute's [Alchemical Symbols](https://www.getty.edu/research/exhibitions_events/exhibitions/alchemy/AoA_symbols.pdf) sheet as a visual reference. That sheet is Getty's and is not included in this repository.

The built-in symbols in `src/alchemy/assets/` are fresh geometric drawings of traditional fire, water, air, earth, and sun symbols. To customize them in a source checkout, drop replacement `fire.png`, `water.png`, `air.png`, `earth.png`, or `sun.png` files into `img/` (see [img/README.md](https://github.com/wulfalpha/alchemy/blob/main/img/README.md)); installed copies can use `--assets-dir`. Square transparent images work best; they display at 48 × 48 pixels.

`python tools/draw_symbols.py --force` regenerates the built-in images in `src/alchemy/assets/`. To ship custom artwork in a distribution, replace the files there before building.

This is an independent prototype. No affiliation with an earlier game is implied; naming and distribution rights have not been legally reviewed.

## Fonts

The game bundles its typefaces so it looks the same on every platform. Headings use [Cormorant](https://github.com/CatharsisFonts/Cormorant) (Garamond, and Infant for its full-height numerals) by Christian Thalmann; interface text uses [Source Sans 3](https://github.com/adobe-fonts/source-sans) by Adobe. Both are under the SIL Open Font License 1.1; the license texts ship beside the fonts in `src/alchemy/assets/fonts/`.

## Development

Rules live in `src/alchemy/board.py`; input and the frame loop live in `src/alchemy/app.py`, and drawing lives in `src/alchemy/render.py`.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src python -m alchemy --smoke-test --seed 42 --screenshot /tmp/alchemy.png
```

The full suite, including the edge-case tests in `tests/edge/`, needs pytest. `uv run` installs the pinned `dev` group (pytest and ruff) automatically:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run pytest -q
uv run ruff check
```

Use `alchemy --seed 42` for a reproducible game.

## License

Released under the [MIT License](https://github.com/wulfalpha/alchemy/blob/main/LICENSE). Copyright (c) 2026 Andrew Davidson. The bundled fonts keep their own SIL Open Font License (see [Fonts](#fonts)).

## Reliability and reaction feedback

The window is resizable: the board keeps its proportions, and mouse controls scale with it. The reaction panel shows base points, longer-line points, unstable-symbol points when a detonation happened, shape points, and the cascade multiplier for the latest reaction.

Scoring is `(25 × unique cleared tiles + 25 × sum of each line's length beyond 4 + 100 × L crossings + 150 × T crossings + 200 × plus crossings) × cascade number`. A four scores 100, a five 150, and a six 200. Two separate fours score 200; two crossing fours score 375 if they form a true plus. Multiple qualifying crossings, including those in solid blocks, each receive the plus bonus. Diagonals never count. In Classic, each extra tile cleared by a detonation adds 50 inside the brackets (see [Unstable symbols](#unstable-symbols-classic)); the tiles of the matched lines themselves score as usual.

Hints cycle through valid swaps without changing future tiles. With `--seed`, restarting intentionally repeats the same experiment.

Use `--assets-dir /path/to/images` for custom PNGs in installed copies. Invalid custom art falls back to packaged symbols with a warning. `--screenshot` supports PNG, JPG, and BMP; extensionless paths get `.png`. The output directory must already exist.

Regenerating existing artwork requires `python tools/draw_symbols.py --force`. This overwrites the packaged defaults in `src/alchemy/assets/`.

Run the full regression suite with `uv run pytest -q`.

## Offline high scores

Completed 30-move experiments are saved automatically after the last cascade. Restarting or quitting an unfinished game does not submit a score. Press **L** or click **Local scores** to view the top ten; **L** or **Esc** returns to the board. The scoreboard does not change the board or prevent a pending cascade from finishing. No account or network connection is used.

Press **P** or click the player name at the top right to edit it. Type a name, then press **Enter** to save or **Esc** to cancel; **Ctrl+A** selects the existing name for replacement. The last saved name is remembered locally. You can also set and remember it with `alchemy --player "Ada"` (16 printable characters maximum; first-use default: Alchemist). Editing pauses pending reactions. Changes apply to unfinished and future experiments; existing score entries keep their original names. Entries show the name, points, and UTC completion date. Ties list the earlier result first. All completed results are retained locally; only the best ten in the current category are displayed.

Normal games, each specific `--seed` challenge, game modes, and scoring-rule versions have separate rankings. Hints remain free and do not disqualify a score. This is a personal scoreboard, not a tamper-proof competitive leaderboard.

Scores are stored in `scores.sqlite3`:

- Windows: `%LOCALAPPDATA%/Alchemy/`
- macOS: `~/Library/Application Support/Alchemy/`
- Linux: `$XDG_DATA_HOME/alchemy/`, or `~/.local/share/alchemy/`

Use `--scores-dir /path/to/folder` or `ALCHEMY_DATA_DIR` to choose another directory. The command-line option takes priority. The game creates the directory when needed. A damaged, unsupported, or unwritable database displays an in-game warning and leaves gameplay available; it is never silently replaced. To back up or reset scores, close the game first, then copy or move `scores.sqlite3`.

## Portable preview builds

The **Desktop preview** GitHub Actions workflow tests and builds portable apps on
pushes/PRs to `main`, or via **Actions → Desktop preview → Run workflow**.
Download the artifact matching your OS/CPU from a successful run, then extract
both the artifact ZIP and the archive inside. See [tester instructions](docs/TESTING.md).
Windows builds use an application folder with UPX disabled and must pass a Defender
scan before upload. Previews are unsigned; no PyPI release is triggered by this workflow.

To build on your own operating system:

```sh
uv run --locked --group build python tools/build_desktop.py
```

The script builds with PyInstaller, launches the packaged executable outside the
source tree with dummy SDL drivers, verifies a rendered screenshot, and writes an
archive plus SHA-256 checksum under `dist/desktop/archives/`. Each platform must
be built on that platform. macOS CI currently targets Apple silicon only.

## Shape reactions and motion

Two intersecting horizontal/vertical runs of **at least four** earn one exclusive
bonus at each crossing, before the cascade multiplier:

- **L: +100** when both lines end at the crossing.
- **T: +150** when one line ends at the crossing.
- **Plus: +200** when neither line ends at the crossing.

All rotations count. Base points still count each tile once, and each maximal
line still earns 25 extra points for every symbol beyond four. A crossing of two
fours therefore scores 275 (L), 325 (T), or 375 (plus). Dense blocks can earn
multiple crossings, with each crossing classified only once.

New games and reshuffles sweep in from a randomly selected side. Matches fade,
then surviving and replacement tiles fall into place. These cosmetic choices
never affect the seeded game's random sequence. Board input waits for tiles to
settle; restart remains available. The name editor pauses the reaction sequence.

Press **A** to toggle remembered reduced motion (no sweeps, fades, or falling
animations). **Tab** inside the local scoreboard switches between new shape
scoring and previous per-line scoring; historical scores are preserved separately.
L and T reactions have their own `l_shape` and `t_shape` sounds.

## Unstable symbols (Classic)

Skilful matches in Classic leave behind an **unstable symbol** of the matched element.
It swaps and matches like any other symbol of its element, but glows and carries a mark
showing its type. When a later match includes it, it **detonates**:

| Earned by | Type | Mark | Detonation clears |
| --- | --- | --- | --- |
| Exactly 5 in a row | **Line** | Two stripes | The whole row or column, in the direction of the match that set it off |
| 6 or more in a row | **Square** | Corner brackets | The 3×3 block around it |
| An L, T, or plus shape | **Element** | A ring | Every symbol of its element on the board |

Rarer patterns earn stronger symbols. On this board, crossing shapes are harder to make
than long lines, so they earn the Element.

- The new symbol forms on the cell you swapped into the pattern, or else on the crossing
  or the middle of the line. It stays in place while the other cleared cells refill.
  A shape earns one symbol for the whole shape, not one per line.
- Cascades can create them too.
- Each extra tile a detonation clears scores **50**, multiplied by the cascade number.
  The matched tiles score as usual. Before a reaction clears, the board highlights
  everything it will take, blasts included.
- An unstable symbol caught in another blast also detonates. A Line set off that way
  clears both its row and column.
- When a dead board is replaced in Classic, the unstable symbols on it are lost to play but
  **banked**. The message line announces it, and the bank's value appears in gold
  under the moves counter.
- When the game ends, every unstable symbol you never detonated pays a flat bonus,
  whether it's still on the board or banked: **Line +100, Square +150, Element +200**.
  The bonus is not multiplied by cascades and is shown on the completion screen.
  A detonation is usually worth more, so using a symbol beats saving it.

Each detonation type has its own sound (`line_burst`, `square_burst`,
`element_burst`), as does forming a new unstable symbol (`unstable`). Adventure
also has unstable symbols (see [Unstable symbols in Adventure](#unstable-symbols-in-adventure));
Diagonal does not. Classic scores are saved under the scoring rules `unstable-v2`.
Scores from 0.1.9, before the unused-symbol bonus, stay in their own
**Classic / without unused-symbol bonus** category, one **Tab** press away.
