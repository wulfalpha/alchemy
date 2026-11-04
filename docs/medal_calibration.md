# Adventure medal calibration — 2026-11-03

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
