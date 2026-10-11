# Alchemy

A Pygame match-four puzzle with independently drawn alchemical symbols and a quiet laboratory aesthetic.

## Install

With Python 3.12+:

```sh
pip install alchemy-game
```

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

- Click a symbol, then an adjacent symbol to swap them.
- Match **four or more** identical symbols horizontally or vertically. Diagonals and groups without a four-symbol line do not clear.
- Valid swaps use one of your 30 moves. Invalid swaps are reversed for free.
- Cleared tiles refill from above; further matches produce cascades.
- Each cleared symbol earns 25 points, with another 25 for each symbol beyond four **in each horizontal or vertical matched line**. A maximal line is scored only once. The total is multiplied by the cascade number. Intersections count each tile once. A true plus adds **200 points per crossing**, before the cascade multiplier: both horizontal and vertical runs must be 4+ symbols and extend on both sides of the crossing. T and L shapes earn their own bonuses, described below.
- **H** or **Hint** highlights a valid swap, without a penalty.
- **R** or **New game** restarts. **C** switches mode. **Esc** quits.
- Boards with no valid swaps are replaced automatically for free; the score and remaining moves carry over.

## Game modes

Three modes are available. Press **C** to switch, or start in one with
`alchemy --mode <key>`. Switching begins a new experiment, and each mode keeps its own
high-score ranking.

| Key | Mode | Symbols | Swaps | Matches run |
| --- | --- | --- | --- | --- |
| `classic-30` | Classic (default) | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `adventure-first-v1` | Adventure | fire, water, air, earth | horizontal and vertical neighbors | rows and columns |
| `diagonal-30` | Diagonal | the four elements plus sun | any touching symbol, diagonals included | rows, columns, and both diagonals |

**Classic** is the primary mode. Four elements for a match-four game keeps about 4.5 legal
swaps available per turn. **Diagonal** adds the sun as a fifth element but lets you swap
and match in every direction, which keeps roughly 11 swaps available and means a dead
board is almost never dealt. A diagonal line earns the same per-symbol and long-line
points as a straight one, but only horizontal and vertical runs form L, T, and plus
crossings.

Classic and Diagonal are 8x8 with 30 moves and the same scoring formula, so only the symbol set and
the directions change. Modes are defined as data in `src/alchemy/modes.py`; adding one is
a `Mode(...)` entry in that file's registry for another 30-move variant.

### Adventure: First Transmutation

Start with `uv run alchemy --mode adventure-first-v1`, or press **C** twice from
Classic. Reach **3,500 points** using the initial 64 tiles and **20 replacement
reactants of each element**. There is no move limit. Matching consumes tiles;
replacement tiles are drawn from the remaining reserves, with no refunds.
When reserves run out, empty spaces remain and cannot be swapped.

The complete cascade scores before success is checked. If no swaps remain,
the game tries up to 200 rearrangements of the existing material. No new tiles
are created by stirring. If none works, the experiment stalls; **R** retries.
The sidebar shows your target, reserves, material remaining (board tiles plus
reserves), and material used. A notice explains when reserves run out. Both
successful and stalled experiments show points, reactants consumed, and successful
swaps; **R** retries the same experiment.

This first experiment defaults to seed **42** so retries repeat the same kit and
random sequence. Use `--seed` for other starting conditions. Successful experiments
save locally under their own experiment revision and seed; stalled and abandoned
attempts do not enter the leaderboard. The initial target is for playtesting;
campaign progression and reactant recovery are future work.

Earlier five-element, straight-lines-only play is retired. Scores set under those rules are
kept and shown as **legacy** scores: open the scoreboard with **L** and press **Tab** to
cycle through current, legacy, and experimental score categories. Both experimental
branches remain accessible under their original mode/rules keys. The historical
diagonal experiment is labeled "straight swaps" to distinguish it from the new
Diagonal mode. Seeded and unseeded results remain separate. Nothing is rewritten or deleted.

## Sounds

Optional sound hooks are ready. Drop WAV or OGG effects into `sounds/` using the filenames in [sounds/README.md](https://github.com/wulfalpha/alchemy/blob/main/sounds/README.md), then restart. Press **M** to mute; use `--volume 0.4` to adjust volume. Missing audio files or devices do not prevent play.

## Artwork

`img/AoA_symbols.pdf` is a visual reference supplied with the project. The game does not extract or display artwork from that PDF.

The five transparent PNGs in `img/` are fresh geometric drawings of traditional fire, water, air, earth, and sun symbols. Replace `fire.png`, `water.png`, `air.png`, `earth.png`, or `sun.png` to customize the game. Square transparent images work best; they display at 48 × 48 pixels.

`python tools/draw_symbols.py` regenerates the default images in both `img/` and `src/alchemy/assets/`. The latter provides packaged fallback assets for installed builds. Copy custom images there as well before building a distribution.

This is an independent prototype. No affiliation with an earlier game is implied; naming and distribution rights have not been legally reviewed.

## Development

Rules live in `src/alchemy/board.py`; rendering and input live in `src/alchemy/app.py`.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src python -m alchemy --smoke-test --seed 42 --screenshot /tmp/alchemy.png
```

The full suite, including the edge-case tests in `tests/edge/`, needs pytest:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run --with pytest pytest -q
```

Use `alchemy --seed 42` for a reproducible game. This first version has session scoring; bundled sound clips and additional modes are not implemented yet.

## License

Released under the [MIT License](https://github.com/wulfalpha/alchemy/blob/main/LICENSE). Copyright (c) 2026 Andrew Davidson.

## Reliability and reaction feedback

The window is resizable: the board keeps its proportions, and mouse controls scale with it. The reaction panel shows base points, longer-line points, plus points, and the cascade multiplier for the latest reaction.

Scoring is `(25 × unique cleared tiles + 25 × sum of each line's length beyond 4 + 100 × L crossings + 150 × T crossings + 200 × plus crossings) × cascade number`. A four scores 100, a five 150, and a six 200. Two separate fours score 200; two crossing fours score 375 if they form a true plus. Multiple qualifying crossings, including those in solid blocks, each receive the plus bonus. Diagonals never count.

Hints cycle through valid swaps without changing future tiles. With `--seed`, restarting intentionally repeats the same experiment.

Use `--assets-dir /path/to/images` for custom PNGs in installed copies. Invalid custom art falls back to packaged symbols with a warning. `--screenshot` supports PNG, JPG, and BMP; extensionless paths get `.png`. The output directory must already exist.

Regenerating existing artwork requires `python tools/draw_symbols.py --force`. This overwrites both custom and packaged defaults.

Run the full regression suite with `uv run --with pytest pytest -q`.

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
Sound clips remain optional; `l_shape` and `t_shape` hooks are ready.
