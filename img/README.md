# Optional symbol artwork

Drop transparent PNGs here to replace the built-in symbols in a source checkout, then restart the game. No code changes required. The defaults ship inside the package (`src/alchemy/assets/`), so this folder only needs the symbols you want to change.

| Filename | Symbol |
| --- | --- |
| fire.png | Fire |
| water.png | Water |
| air.png | Air |
| earth.png | Earth |
| sun.png | Sun (Diagonal mode only) |

Square images work best; they display at 48 × 48 pixels. Missing or unreadable files fall back to the built-in artwork. Installed copies of the game can use `alchemy --assets-dir <folder>` instead.
