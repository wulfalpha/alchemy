# Optional sound effects

Drop short `.wav` or `.ogg` files here, then restart the game. No code changes required. WAV takes priority if both formats exist. Missing effects are silent; invalid files are logged and skipped. The game also runs without an audio device.

| Filename | Trigger |
| --- | --- |
| select.wav | Select a tile |
| swap.wav | Accept a valid swap |
| invalid.wav | Reject a swap that makes no match |
| match.wav | Clear the first match |
| cascade.wav | Clear each subsequent cascade |
| plus.wav | Award a plus bonus (alongside match/cascade) |
| hint.wav | Show a hint |
| shuffle.wav | Automatically replace a dead board |
| restart.wav | Start a new game with R or the button |
| game_over.wav | Finish the last move, after all cascades |

Use brief clips; effects can overlap. `plus` plays once per clear even with multiple crosses. No audio is bundled yet.

Press **M** to mute/unmute. Default volume is 60%. Example:

```sh
uv run alchemy --volume 0.4 --sound-dir /path/to/my/sounds
uv run alchemy --mute
```

`--sound-dir` overrides the default search directories. For distribution, place effects under `src/alchemy/assets/sounds/` before building; this is the fallback when running an installed package. Keep any required attribution/license information with sounds you add.
