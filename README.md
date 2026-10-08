# Alchemy

A Pygame match-four puzzle with independently drawn alchemical symbols and a quiet laboratory aesthetic.

## Play

With Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```sh
uv run alchemy
```

Or install into your Python environment with `python -m pip install -e .`, then run `alchemy`.

- Click a symbol, then an adjacent symbol to swap them.
- Match **four or more** identical symbols horizontally or vertically. Diagonals and groups without a four-symbol line do not clear.
- Valid swaps use one of your 30 moves. Invalid swaps are reversed for free.
- Cleared tiles refill from above; further matches produce cascades.
- Each cleared symbol earns 25 points, with another 25 for each symbol beyond four. The total is multiplied by the cascade number. Intersections count each tile once. A true plus adds **200 points per crossing**, before the cascade multiplier: both horizontal and vertical runs must be 4+ symbols and extend on both sides of the crossing. T and L shapes do not earn this bonus.
- **H** or **Hint** highlights a valid swap, without a penalty.
- **R** or **New game** restarts. **Esc** quits.
- Boards with no valid swaps are replaced automatically for free; the score and remaining moves carry over.

## Sounds

Optional sound hooks are ready. Drop WAV or OGG effects into `sounds/` using the filenames in [sounds/README.md](sounds/README.md), then restart. Press **M** to mute; use `--volume 0.4` to adjust volume. Missing audio files or devices do not prevent play.

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

Use `alchemy --seed 42` for a reproducible game. This first version has session scoring; persistent high scores, bundled sound clips, and additional modes are not implemented yet.
