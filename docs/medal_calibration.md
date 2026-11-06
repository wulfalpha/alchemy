# Adventure medal calibration — 2026-11-03

*Update 2026-11-05: unstable symbols in Adventure raise the thresholds for the new
revisions to **Silver 40, Gold 50**. See [Recalibration with unstable
symbols](#recalibration-with-unstable-symbols--2026-11-05). The 2026-11-03 thresholds
below still apply to wins from earlier revisions.*

Selected initial thresholds: **Bronze for a win, Silver at 30 material left,
Gold at 45**. Material is board tiles plus reserves after the complete winning
cascade. A stalled or unfinished run cannot earn a medal. The same thresholds
apply to all difficulties and unlimited Adventure; stir limits already separate
the challenges, and score categories stay separate.

## Method

The committed `tools/measure_adventure.py` runs the real game to completion.
Two policies use separate move-choice RNGs (`Random(10000 + run_index)`), so
choosing a move never consumes the game's RNG:

- Random chooses uniformly from legal swaps.
- Efficient maximizes visible first-reaction points per cleared tile, breaks ties
  by immediate points, then randomly. It includes line/shape bonuses but ignores
  unseen refill tiles and future cascades. It is a limited heuristic, not an
  expert player or a search for the best achievable score.

For each of four variants, each policy played 60 runs on seeds 0–59 and another
60 on fixed seed 42: **960 runs total**. Fixed-seed repetitions vary move choices,
not starting boards. Variants share the seed/choice schedule, so results across
limits are paired rather than independent observations. The raw results are in
[medal_calibration.json](medal_calibration.json).

Reproduce from the repository with the project dependencies installed:

```sh
uv run python tools/measure_adventure.py --runs 60
uv run python tools/measure_adventure.py --runs 60 --seed 42
```

## Results

Each row is 60 attempts. Silver+ counts include Gold; medal counts are among wins.

| Starting seeds | Mode | Policy | Wins | Median material on wins | Silver+ (30+) | Gold (45+) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0–59 | Unlimited | Random | 60 | 32 | 33 | 11 |
| 0–59 | Unlimited | Efficient | 59 | 28 | 27 | 7 |
| 0–59 | Easy | Random | 59 | 32 | 33 | 11 |
| 0–59 | Easy | Efficient | 59 | 28 | 27 | 7 |
| 0–59 | Medium | Random | 52 | 33 | 33 | 11 |
| 0–59 | Medium | Efficient | 58 | 28 | 27 | 7 |
| 0–59 | Hard | Random | 41 | 37 | 31 | 11 |
| 0–59 | Hard | Efficient | 42 | 32.5 | 26 | 7 |
| 42 | Unlimited | Random | 60 | 20 | 14 | 3 |
| 42 | Unlimited | Efficient | 60 | 22.5 | 16 | 5 |
| 42 | Easy | Random | 60 | 20 | 14 | 3 |
| 42 | Easy | Efficient | 59 | 23 | 16 | 5 |
| 42 | Medium | Random | 48 | 25.5 | 14 | 3 |
| 42 | Medium | Efficient | 46 | 26 | 16 | 5 |
| 42 | Hard | Random | 26 | 31 | 14 | 3 |
| 42 | Hard | Efficient | 23 | 32 | 13 | 5 |

## Interpretation and decision

Bronze celebrates completing the target even with no material left. Thirty makes
Silver attainable but above the median default-seed win on Easy and Medium.
Forty-five makes Gold a rarer stretch goal: 3–5 of 60 attempts per policy on the
default seed, and 7–11 of 60 across the seed sweep. A win with 15 material left
therefore earns Bronze and has a clear next goal.

Hard's higher median among wins does not mean it is easier: the stir cap removes
many less efficient runs before completion. Keep the same thresholds across
levels rather than grading only the survivors against different cutoffs.

The efficient heuristic does not consistently beat random play. These data show
achievable material ranges, not that medals isolate skill from luck. Seed 42 also
has lower medal rates than the seed sweep. Human playtesting should evaluate
whether Silver feels reachable and Gold rewards deliberate planning. No changes
to the 3,500 target, reserves, stirring, leaderboard ranking, or RNG were made.

## Recalibration with unstable symbols — 2026-11-05

The new revisions (`adventure-first-v3`, `adventure-3-v2`, `adventure-5-v2`,
`adventure-8-v2`) add unstable symbols. The efficient policy now ranks a move by
first-reaction points per tile of material it spends, counting detonations and newly
formed symbols (a new symbol keeps its tile). With unstable symbols off, that ranking
is identical to the original: `--before` reproduces
[medal_calibration.json](medal_calibration.json) exactly. Same seeds, choice RNGs,
and 960-run schedule. Raw results are in
[medal_calibration_unstable.json](medal_calibration_unstable.json).

```sh
uv run python tools/measure_adventure.py --runs 60            # current revisions
uv run python tools/measure_adventure.py --runs 60 --seed 42
uv run python tools/measure_adventure.py --runs 60 --before   # released revisions
```

Before → after, 60 attempts per row:

| Starting seeds | Mode | Policy | Wins | Median material on wins | 30+ | 45+ |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0–59 | Unlimited | Random | 60 → 60 | 32 → 31.5 | 33 → 33 | 11 → 11 |
| 0–59 | Unlimited | Efficient | 59 → 60 | 28 → 44 | 27 → 52 | 7 → 28 |
| 0–59 | Hard | Random | 41 → 47 | 37 → 36 | 31 → 31 | 11 → 11 |
| 0–59 | Hard | Efficient | 42 → 58 | 32.5 → 44 | 26 → 52 | 7 → 28 |
| 42 | Unlimited | Random | 60 → 60 | 20 → 24 | 14 → 16 | 3 → 4 |
| 42 | Unlimited | Efficient | 60 → 60 | 22.5 → 37.5 | 16 → 48 | 5 → 11 |
| 42 | Medium | Efficient | 46 → 58 | 26 → 38 | 16 → 48 | 5 → 11 |
| 42 | Hard | Random | 26 → 32 | 31 → 29.5 | 14 → 16 | 3 → 4 |
| 42 | Hard | Efficient | 23 → 50 | 32 → 38 | 13 → 45 | 5 → 10 |

Easy and Medium track Unlimited closely in the seed sweep; all rows are in the JSON.

Two findings:

- **Skill now separates from luck.** The original efficient policy did not
  consistently beat random play. With unstable symbols it clearly does: on the
  default kit, three times as many 30+ wins and nearly three times as many 45+ wins.
  Random play barely changes, because it does not exploit the mechanic.
- **The old thresholds became easy.** On the default kit the efficient policy's
  median win (37.5) exceeded Silver at 30, and it reached Silver in 48 of 60 runs.

Material reached on the default kit (seed 42), unlimited Adventure, among 60 runs:

| Policy | 35+ | 40+ | 45+ | 50+ |
| --- | ---: | ---: | ---: | ---: |
| Random | 11 | 8 | 4 | 2 |
| Efficient | 42 | 25 | 11 | 6 |

**Decision:** Silver 40, Gold 50 for the new revisions. That restores the original
intent: Silver sits just above the efficient median win (25 of 60), and Gold is a
stretch goal (6 of 60 efficient, 2 random). Thresholds are now stored per experiment
revision (`Experiment.medals`), so wins from earlier revisions keep Silver 30 and
Gold 45 and never change award. As before, one-move lookahead understates a planning
human, and human playtesting should confirm the targets.

