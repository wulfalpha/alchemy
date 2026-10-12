# Adventure mode: review and suggestions

I reviewed commit `bfd7cb5` ("Add finite-reactant Adventure mode for 0.1.5"), on 2026-10-12, without changing the repo. All numbers come from headless playouts of the real game rules (`src/alchemy/adventure.py`) plus a few runs of the real app loop with scripted clicks. The simulation scripts (`sim/`) and screenshots referenced below are not committed to the repo; they can be added on request.

## How Adventure works today

- **One experiment, "First Transmutation"** (`adventure.py:9-19`). It uses the four elements on an 8×8 board, with straight-line matches of 4 or more and the same scoring as Classic, including the L/T/plus bonuses and the cascade multiplier.
- **The goal is to reach 3,500 points.** There's no move limit (`modes.py:190-203`, `moves=None`).
- **The kit is finite.** It's the 64 starting tiles plus 20 reserve tiles of each element, 144 in total. Cleared tiles are refilled by weighted draws from the reserves (`finite_refill`, `adventure.py:22-41`). Once the reserves are empty, the gaps stay empty and can't be swapped.
- **The seed is fixed at 42** unless `--seed` is passed, so every attempt deals the same kit and starting board (`adventure.py:15,70`).
- **Dead boards get "stirred."** The game makes up to 200 random attempts to rearrange the same tiles into a layout that has a legal move and no ready-made match (`stir`, `adventure.py:44-64`). If that fails, the outcome is `stalled` (`adventure.py:98-113`).
- **Success is checked only after the whole cascade has finished**, so the final reaction always counts in full.
- **The UI shows** the target, the four reserve counts, material left, tiles used, swaps made, and an end screen with tiles consumed and swaps (`app.py:303-362`).
- **Scores are saved only for successful runs**, under mode key `adventure-first-v1` and the seed (`app.py:258-262`).
- **There is no saving or resuming of a run in progress.** R, C and Esc all discard it.

**What's good:** the rules are clean, and they really do conserve material. Tests check that board tiles plus reserves plus tiles consumed always equals the starting total, and the existing suite passes: **227 passed**, with no Adventure failures. Gravity with empty cells, compacted columns and "never mint material" are all correct. Checking success only after the full cascade is fair. Adventure is a thin subclass of `Game` (`_refill` and `_settle` are its only rule overrides), so the shared engine stays simple. The design notes in `improvements.md` are careful and match the code. The sparse endgame, where you work with whatever material is left, is a genuinely new feel compared with Classic.

## What I measured

Four automated players:
- **random:** picks any legal swap.
- **first:** always takes the first hinted swap.
- **greedy:** takes the swap with the best immediate score, cascades included.
- **efficient:** takes the swap with the best points per tile consumed.

| Run set | Win rate at 3,500 | Swaps to win (median) | Material left at win (median) | Highest score possible by playing on until the material runs out: p10 / median / p90 / max |
|---|---|---|---|---|
| random, seed 42, 500 runs | **100%** | 26 | 22 | 3,650 / 3,950 / 4,400 / 6,500 |
| random, seeds 0–199 ×3 (600) | 99.8% | 24 | 25 | 3,700 / 4,050 / 4,600 / 6,050 |
| first-hint, seeds 0–199 | 99.0% | 27 | 20 | 3,600 / 3,900 / 4,400 / 5,700 |
| greedy, seeds 0–199 | 100% | **15** | **48** | 4,050 / 4,700 / 5,400 / 9,825 |
| efficient, seeds 0–199 | 100% | 15 | 48 | 4,050 / 4,675 / 5,400 / 9,975 |

More numbers, for seed 42 unless noted:
- **Starting board** (seed 42): fire 20, water 18, air 16, earth 10, so the total kit is uneven (fire 40 vs earth 30).
- **Run length:** the reserves run out around swap 17 under random play (swap 12 under greedy). A random-play win takes a median of 9 more swaps after that, which earn about 1,100 points, roughly 31% of the target.
- **Recorded scores:** 43% of random wins end at exactly 3,500 and 46% at exactly 3,550. Greedy's median recorded score is also 3,550, the same as random.
- **Skill does show, in material and swaps:**
  - Greedy wins seed 42 in 9 swaps with 63 tiles left.
  - Only 8.8% of random wins finish with 40 or more tiles left, and only 3.2% finish within 15 swaps.
- **Highest possible score** (seed 42, random play): 43% of runs could reach 4,000, 9% could reach 4,500, and 1.4% could reach 5,000. Across 200 seeds, greedy reaches 5,000 in 30% of runs.
- **Stirs:** random play on seed 42 averages 4.3 stirs per winning run, and every run stirs at least once. When play continues to exhaustion, the average rises to 7.7 stirs.
- **Forced moves:** about 6 swaps per random run on seed 42 have exactly one legal option. When play continues to exhaustion, that rises to about 9 out of about 30.
- **Legal swaps per turn:** 3.2–4.4 on average.
- **Stalls when playing on to exhaustion:**
  - 97–100% happen because fewer than 4 tiles of any element remain, so no match is possible.
  - About 1.6% (8 of 500 on seed 42, and 11 of 600 across seeds) are **false stalls**: 200 stir attempts failed, but 20,000 attempts found a valid layout.
  - At the real 3,500 target there were only 3 stalls in 1,300 runs. All were plain material exhaustion, 50–100 points short of the target.
- **No softlocks in the game loop:** every run ended with exactly one `game_over`.

---

## 1. Bugs and softlocks found

**B1. The stir search gives up when a valid layout exists ("false stall").** Severity: low today, higher once targets rise.
- **Reproduce:** `python sim/repro_false_stall.py`. It plays seed 42 with the target raised to 999,999, using random choices from `Random(32)`.
- **Observed:** the game ends `stalled` with the message "no playable layout found". Nine tiles are left (3 fire, 4 air, 2 earth).
- **Expected:** a valid layout exists. `stir(..., attempts=20000)` finds the bottom row `A F A A A F . E`, where swapping (0,7) with (1,7) makes four airs.
- **Where:** `adventure.py:49-64`. The random search samples whole-board permutations, so on a sparse board the chance of hitting one of the few playable layouts is tiny.
- **Fix:** for sparse boards (say 16 tiles or fewer), build a layout directly instead of searching at random:
  - Put three of the most common element in the bottom row, a different tile in the fourth spot, and the fourth matching tile on top of it.
  - Scatter the rest without making a match.
  - Or enumerate every layout when the tile count is small.
- **Impact today:** at target 3,500 the player almost always wins before this point, so it was never observed there. Any harder experiment will hit it. Players would see an unfair loss.

**B2. The stall message blames the layout search when the material is simply gone.** Severity: UX, reproduced.
- **Reproduce:** `python sim/repro_message.py`. Four tiles are left, none of them four of a kind, and the message still reads "Experiment stalled: no playable layout found."
- **Where:** `adventure.py:47-48` returns `False` without saying why, `adventure.py:111` sets the message, and `app.py:356-357` shows "No playable layout found. Try again!"
- **Fix:** have `stir` return a reason, and say "Out of material: fewer than four of any element remain (12 tiles stranded)". Also show the gap ("50 points short").

**B3. Adventure's scoreboard Tab cycles into Classic's legacy score categories.** Severity: minor UX, reproduced.
- **Reproduce:** `score_categories('adventure-first-v1', 'Adventure')` returns Adventure's own category, then four `classic-30` legacy categories.
- **Effect:** pressing Tab in Adventure's scoreboard shows Classic legacy scores filtered by seed 42.
- **Where:** `scores.py:35-37`, which always appends `HISTORICAL_CATEGORIES`, used by `app.py:112,190`.
- **Fix:** only append the historical categories for `classic-30`.

**B4. (Possible) The leaderboard key doesn't include the experiment settings.** Scores are partitioned by mode key, scoring rules and seed (`app.py:260-261`, `scores.py:136-146`). The target and reserves (`Experiment`) are not part of the key. Changing the target or kit without also renaming `adventure-first-v1` would silently mix incomparable results. Today this depends on remembering to bump the key, and the README says results are stored "under their own experiment revision". **Fix:** derive the key from a hash of the `Experiment` fields, or add a `revision` field to `Experiment` and assert on it in a test.

**B5. (Design risk) A whole run can be lost with one key and no confirmation.** R, C and the New game button all call `start_new_game()` immediately (`app.py:200-208`, `app.py:222-224`), even mid-run. Runs are short (15–30 swaps), so this costs minutes, not hours. It still deserves a confirmation, or an undo, once runs get longer or experiments chain together.

No real softlocks: every run ended with exactly one `game_over`, and input is correctly blocked after the game finishes.

## 2. Balance and difficulty

1. **The 3,500 target is almost impossible to miss, so the only experiment has no tension.**
   - Random clicking wins 100% of 500 seed-42 runs, and even the lowest highest-possible score among them was exactly 3,500.
   - Suggestion: keep 3,500 as the pass mark, and add **graded targets** taken from the measured highest-possible scores on seed 42:
     - pass at 3,500 (100% of random runs could reach it)
     - "silver" at about 4,250 (between random-play median and p90)
     - "gold" at about 5,000 (1.4% of random runs, 30% of greedy runs across seeds)
2. **The game stops the moment you pass the target, so skill is invisible.**
   - Greedy and random both record a median of 3,550.
   - The real skill signal is efficiency: greedy wins seed 42 in 9 swaps with 63 tiles left, while random needs a median of 26 swaps and leaves 22.
   - Idea: rank and grade by **material left at completion** or swaps used, not points. Or offer "Continue the experiment" after success, so the player can push their score until the material runs out.
3. **The kit isn't designed.** Seed 42's starting board is generated randomly (`Game.__init__` → `new_grid`), so the kit is lopsided: fire 40, earth 30. Idea: give `Experiment` an explicit starting composition or board, so each experiment is designed rather than an accident of the seed.
4. **The stir is a free and frequent rescue.** Every random run on seed 42 stirs at least once (4.3 times on average), and each stir rearranges the whole board. That softens the finite-material idea and makes the endgame feel random. Ideas:
   - Allow a limited number of stirs per experiment, shown as a "stirring rod" with 3 uses.
   - Or charge material for each stir (one tile of the most common element).
   - Or only rearrange the tiles that have to move.
5. **The endgame is often a forced move.** About 6 swaps per run on seed 42 have only one legal option, and about 9 when play continues to exhaustion. Ideas: let the player see when that's coming (highlight "last reaction possible"), or keep variety up with partial recovery (the planned refunds), so the last third of the run still involves decisions.
6. **Nothing ramps up.** With a single experiment there is no difficulty curve at all. See section 4 for a sequence.

## 3. Progression and rewards

- **Ideas:**
  - A short **sequence of experiments** that unlock one after another. Store the furthest experiment reached and the best grade for each in the existing SQLite `settings`/`scores` tables (`scores.py:67-71`).
  - **Grades per experiment** (pass/silver/gold, or alchemical seals), based on points and material left. These are cheap to add, because `AdventureGame` already tracks `consumed`, `turns` and `material_left`.
  - **Recovered material as a reward**, as already drafted in `improvements.md`:
    - A 5+ line recovers 1 tile.
    - An L, T or plus recovers 2.
    - Recovery is always less than the tiles consumed.

    This makes shape-building the strategic skill, rather than just a points bonus.
  - **Carry-over between experiments.** Leftover reserves become a small bonus in the next experiment, so finishing efficiently pays off later.
- **Keep:** saving only successful runs to the leaderboard. Recording stalled runs would clutter it.

## 4. Level and objective variety (ideas that fit the current engine)

Each idea below is marked with implementation effort. They all reuse `Experiment` (as a data record), `finite_refill`, `matched_runs`, `shape_crossings` and `last_reaction`.

| # | Objective idea | How it maps to the engine | Effort |
|---|---|---|---|
| O1 | **Graded score targets** (3,500 / 4,250 / 5,000) on the same kit | Add a `targets` tuple to `Experiment`; `_settle` records the grade, and you can optionally continue after the pass mark | Small |
| O2 | **Efficiency trial:** reach 3,500 with at least 40 tiles left (8.8% of random runs on seed 42) or within 15 swaps (3.2%) | Compare `material_left` / `turns` in `_settle` | Small |
| O3 | **Element quota:** transmute 30 water and 20 earth | Count per-element tiles cleared in `_refill` before refilling (`self.pending` holds the cells) | Small |
| O4 | **Scarce-element kit:** reserves like (30, 30, 30, 5) | Already possible: just change `reserves` | Small |
| O5 | **Shape recipe:** make 2 T reactions and 1 plus | Count `shape_crossings` results in `resolve`; the events already include `t_shape` and `plus` | Small–medium |
| O6 | **Purify the vessel:** remove every earth tile from the board and reserves | Win when that element's count in the board and reserves is 0 | Small |
| O7 | **Cascade experiment:** reach a ×3 cascade | `self.chain` is already tracked | Small |
| O8 | **Fixed authored board ("puzzle plate")** with an exact solution | Let `Experiment` supply `grid`; skip `new_grid`; no reserves | Medium |
| O9 | **Catalyst tiles**, which aren't consumed when matched and return to the reserves | Needs a tile flag; touches `finite_refill` and rendering | Medium |
| O10 | **Inert lead tiles** that only clear when next to a match | A new tile kind that never matches; clears as a side effect | Medium–large |
| O11 | **Diagonal experiment:** Adventure rules on the `DIAGONALS` mode | `AdventureGame` hard-codes `ADVENTURE` (`adventure.py:71`); take the mode from `Experiment` | Medium |
| O12 | **Recipe transmutation:** clearing 4+ fire next to water creates one "steam" or "sun" tile (the fifth symbol already exists) | New combination rules in `resolve`; the art already exists in `WITH_SUN` | Large |

## 5. Narrative and theming (ideas)

- **Frame the campaign as the magnum opus.** Use the four classic stages as chapters:
  - **Nigredo** (blackening): scarce kits and purification objectives (O4, O6).
  - **Albedo** (whitening): efficiency and cleansing (O2).
  - **Citrinitas** (yellowing): shape recipes (O5), introducing the sun symbol.
  - **Rubedo** (reddening): the final transmutation, combining several objectives.
- **Use the four elements as reagent bottles.** The sidebar already lists "Fire: 20". Draw each as a draining flask, and when it runs out show a short note such as "The water flask is dry."
- **Give each experiment a one-line notebook entry**, e.g. "Calcination: burn away the excess earth." This would sit in an `Experiment.notes` field and show where the "practice" lines go today (`app.py:323-325`).
- **Rename the mechanics in theme:**
  - "Stir" is already nicely in theme; make it a visible tool (the stirring rod).
  - Recovered material could be called "distillate".
  - A stall could read "The reaction has gone cold."
- **The sun symbol**, currently only in Diagonal mode, could be Adventure's reward or goal tile: "gold" made by transmutation.

## 6. UX, feedback and onboarding

- **Show progress toward the target.** Add a bar or "1,150 to go" under "Target" (`app.py:311`). Right now the player has to compare two numbers in their head.
- **Explain stirs.** A stir replaces the whole board with a short entrance animation, and the only explanation is the message line. Count them in the sidebar ("Stirs: 2"), and once stirs are limited, show how many remain.
- **On the end screen:**
  - When the run stalls, show how far short the player fell and what material was stranded (B2).
  - When it succeeds, show the grade and material left. Today it says "New local high score!" even for a routine 3,500.
- **Add an onboarding run.** The first time someone plays Adventure, run a short guided experiment with 4 tiles of each element in reserve. It would teach that refills come from the bottles and aren't charged twice, which `improvements.md` already flags as needing explanation.
- **Small polish:**
  - "MATERIAL LEFT" is zero-padded (`08`, `app.py:304`, `{remaining:02d}`). That suits a move counter but looks odd for material.
  - Colour-code each reserve count by how full it is.
- **Warn before discarding a run.** R and C mid-run should ask "Abandon this experiment?" (B5).

## 7. Save and replay

- **There's no saving mid-run.** A run is short today, so this matters most once a campaign exists. Idea: since runs are fully deterministic (seed plus move list), save just the seed and the list of swaps, and replay them on load. Existing tests already prove determinism (`tests/test_adventure.py:94-110`), so this is cheap and robust. Hints and animations don't consume the random sequence.
- **Use the same move log for replays and "ghosts":** show the best run's swap count, or let the player watch it.
- **The same seed on every retry is good for fairness**, but it means the opening is memorizable. Ideas: a "daily experiment" seed (date-based, its own leaderboard), alongside the fixed seed 42 for practice.
- **Leaderboard:** store material left and swaps alongside points (a schema addition in `scores.py:67-70`). That makes it possible to rank Adventure by efficiency (section 2, point 2).

---

## Prioritized next steps

1. **Fix B2 and B3** (correct stall message and shortfall; Adventure-only score categories). Small.
2. **Add graded targets and rank by efficiency** (O1 and O2; store material left and swaps). This gives the existing experiment real tension and makes skill visible. Small.
3. **Make stir build sparse layouts directly** (B1) before adding any harder target. Small–medium.
4. **Limit or charge for stirs, and give `Experiment` an authored starting composition.** Then re-run `sim/sim.py` to retune the targets. Medium.
5. **Build a 4–6 experiment Nigredo→Rubedo sequence** from O3–O7, with unlock and grade persistence and a seed-plus-move-log save. Medium.
6. **Recovery/distillate and the recipe ideas** (O9, O12) once the core loop has been playtested. Large.

## Reproducing the numbers

```sh
cd sim
python sim.py random '[42]' 500 3500        # strategies: random | first | greedy | efficient
python sim.py greedy 'range(200)' 1 999999  # 999999 = keep playing until the material runs out (highest possible score)
python analyze.py
python repro_false_stall.py; python repro_message.py
python shots.py start ../adventure_start.png   # also: sparse; shot_end.py plays the real app loop
```

These scripts are not in the repo yet. They expect a local checkout on `sys.path` and pygame installed. The simulations took about 2 minutes in total.
