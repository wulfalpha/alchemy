"""Smoke-test the built wheel outside the source tree, in a fresh environment."""
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    wheels = list(Path('dist').glob('*.whl'))
    if len(wheels) != 1:
        raise SystemExit('Expected exactly one wheel in dist/')
    wheel = wheels[0].resolve()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        environment = root / 'venv'
        subprocess.run(['uv', 'venv', str(environment)], check=True)
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        subprocess.run(['uv', 'pip', 'install', '--python', str(python), str(wheel)], check=True)
        env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        env.pop('PYTHONPATH', None)
        subprocess.run([str(python), '-m', 'alchemy', '--smoke-test'],
                       cwd=root, env=env, check=True)


if __name__ == '__main__':
    main()
