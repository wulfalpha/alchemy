# Testing a portable Alchemy build

Download the artifact for your operating system and CPU from the **Desktop preview**
GitHub Actions run. GitHub requires you to sign in to download workflow artifacts.
Extract the downloaded artifact, then extract the archive inside it.

- Windows x64: open `Alchemy/Alchemy.exe`. Keep the entire folder together.
- macOS Apple silicon: open `Alchemy.app`. This build does not target Intel Macs.
- Linux x64: run `Alchemy/Alchemy`. Built on Ubuntu 22.04; other distributions may
  require compatible system graphics/audio libraries.

Python is not required. These preview builds are unsigned and macOS builds are
not notarized. An OS trust warning is possible. Report warnings or antivirus
findings with their exact text; do not disable antivirus to run a build.

Windows artifacts are uploaded only after a successful Defender custom scan.
A clean scan is not a guarantee of acceptance by every antivirus product.

Try a full 30-move game, resize the window, open scores with L, edit your name
with P, and restart the app to confirm scores and names persist. Existing local
scores are shared with the Python-installed game. To use isolated test scores,
launch the executable with `--scores-dir` pointing to a temporary folder.

Report problems at https://github.com/wulfalpha/alchemy/issues with:

- The contents of BUILD.txt and your OS version / CPU type.
- Steps to reproduce, expected behavior, and actual behavior.
- Any error message or screenshot (without private information).

Preview builds do not publish to PyPI. Archives and SHA-256 checksums are kept
as workflow artifacts for 14 days.
