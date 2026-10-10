"""Build, smoke-test, and archive a portable application on the current OS."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'dist' / 'desktop'
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--onedir', '--noupx', '--name', 'Alchemy', '--paths', str(ROOT / 'src'),
               '--collect-data', 'alchemy', '--distpath', str(output),
               '--workpath', str(ROOT / 'build' / 'desktop'),
               '--specpath', str(ROOT / 'build')]
    if sys.platform in ('win32', 'darwin'):
        command.append('--windowed')
    build_env = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / 'build' / 'pyinstaller-cache'))
    subprocess.run(command + [str(ROOT / 'tools' / 'desktop_entry.py')], check=True, cwd=ROOT, env=build_env)
    bundle = output / ('Alchemy.app' if sys.platform == 'darwin' else 'Alchemy')
    executable = (bundle / 'Contents' / 'MacOS' / 'Alchemy' if sys.platform == 'darwin'
                  else bundle / ('Alchemy.exe' if sys.platform == 'win32' else 'Alchemy'))
    with tempfile.TemporaryDirectory() as temporary:
        env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                   ALCHEMY_DATA_DIR=temporary)
        env.pop('PYTHONPATH', None)
        screenshot = Path(temporary) / 'smoke.png'
        subprocess.run([str(executable), '--smoke-test', '--screenshot', str(screenshot)],
                       cwd=temporary, env=env, check=True, timeout=60)
        if not screenshot.is_file() or screenshot.stat().st_size == 0:
            raise RuntimeError('Packaged application did not render a frame')
    version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
    label = f'Alchemy-{version}-{revision}-{platform.system()}-{platform.machine()}'
    archives = output / 'archives'
    archives.mkdir(exist_ok=True)
    # A tar archive retains executable modes and symlinks on Linux/macOS.
    with tempfile.TemporaryDirectory() as staging:
        stage = Path(staging)
        shutil.copytree(bundle, stage / bundle.name, symlinks=True)
        shutil.copy2(ROOT / 'LICENSE', stage / 'LICENSE')
        shutil.copy2(ROOT / 'docs' / 'TESTING.md', stage / 'TESTING.md')
        (stage / 'BUILD.txt').write_text(f'{label}\nPython {platform.python_version()}\n', encoding='utf-8')
        archive = Path(shutil.make_archive(str(archives / label),
                       'zip' if sys.platform == 'win32' else 'gztar', stage))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + '.sha256').write_text(f'{digest}  {archive.name}\n')
    print(f'Portable build ready: {archive}')


if __name__ == '__main__':
    main()
