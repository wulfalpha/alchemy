"""Offline, transactional scores, separated by mode and scoring rules."""
from datetime import datetime, timezone
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import sys

RULES = 'shapes-v3'          # four-element Classic and Diagonal
LEGACY_RULES = 'shapes-v2'   # retired five-element orthogonal play
OLDEST_RULES = 'per-line-v1'
# Released formula keys retained for compatibility; UI categories also include experiments.
RULE_HISTORY = (RULES, LEGACY_RULES, OLDEST_RULES)
RULE_LABELS = {RULES: 'Local high scores',
               LEGACY_RULES: 'Legacy scores / five elements',
               OLDEST_RULES: 'Legacy scores / per-line'}
MODE = 'classic-30'


@dataclass(frozen=True)
class ScoreCategory:
    label: str
    mode: str
    rules: str


HISTORICAL_CATEGORIES = (
    ScoreCategory('Five elements / straight swaps', MODE, LEGACY_RULES),
    ScoreCategory('Legacy / per-line scoring', MODE, OLDEST_RULES),
    ScoreCategory('Four-element experiment', MODE, 'four-elements-experiment-v1'),
    ScoreCategory('Diagonal experiment / straight swaps', MODE, 'diagonals-experiment-v1'),
)


def score_categories(mode_key, mode_label):
    """Current ranking first, then original historical partitions (never migrated)."""
    current = (ScoreCategory(f'{mode_label} / current', mode_key, RULES),)
    if mode_key.startswith('adventure-'):
        history = (() if mode_key == 'adventure-first-v1' else
                   (ScoreCategory('First Transmutation / original rules', 'adventure-first-v1', RULES),))
        return current + history
    return current + HISTORICAL_CATEGORIES


def clean_player(name):
    return ''.join(c for c in name if c.isprintable()).strip()[:16] or 'Alchemist'


def data_directory():
    override = os.environ.get('ALCHEMY_DATA_DIR')
    if override:
        return Path(override)
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'Alchemy'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'Alchemy'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'alchemy'


class Scoreboard:
    def __init__(self, directory=None):
        self.path = (Path(directory) if directory is not None else data_directory()) / 'scores.sqlite3'
        self.error = None
        self.connection = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path, timeout=1)
            version = self.connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2):
                raise sqlite3.DatabaseError('Unsupported scoreboard version')
            with self.connection:
                self.connection.execute('''CREATE TABLE IF NOT EXISTS scores (
                    id TEXT PRIMARY KEY, player TEXT NOT NULL, score INTEGER NOT NULL,
                    completed TEXT NOT NULL, mode TEXT NOT NULL, rules TEXT NOT NULL,
                    seed TEXT NOT NULL)''')
                self.connection.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                columns = {row[1] for row in self.connection.execute('PRAGMA table_info(scores)')}
                for column in ('material_left', 'swaps', 'stirs'):
                    if column not in columns:
                        self.connection.execute(f'ALTER TABLE scores ADD COLUMN {column} INTEGER')
                self.connection.execute('PRAGMA user_version = 2')
        except (OSError, sqlite3.Error) as error:
            self._failed(error)

    def _failed(self, error):
        self.error = f'Local scores unavailable: {error}'
        self.close()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def reduced_motion(self):
        if self.connection is None:
            return False
        try:
            row = self.connection.execute("SELECT value FROM settings WHERE key='reduced_motion'").fetchone()
            return row is not None and row[0] == '1'
        except sqlite3.Error as error:
            self._failed(error)
            return False

    def set_reduced_motion(self, enabled):
        if self.connection is not None:
            try:
                with self.connection:
                    self.connection.execute("INSERT OR REPLACE INTO settings VALUES ('reduced_motion', ?)", ('1' if enabled else '0',))
            except sqlite3.Error as error:
                self._failed(error)

    def player(self):
        if self.connection is None:
            return 'Alchemist'
        try:
            row = self.connection.execute("SELECT value FROM settings WHERE key='player'").fetchone()
            return clean_player(row[0]) if row else 'Alchemist'
        except sqlite3.Error as error:
            self._failed(error)
            return 'Alchemist'

    def set_player(self, name):
        name = clean_player(name)
        if self.connection is not None:
            try:
                with self.connection:
                    self.connection.execute("INSERT OR REPLACE INTO settings VALUES ('player', ?)", (name,))
            except sqlite3.Error as error:
                self._failed(error)
        return name

    def top(self, seed=None, mode=MODE, rules=RULES):
        if self.connection is None:
            return []
        try:
            rows = self.connection.execute('''SELECT player, score, completed, id, material_left, swaps, stirs FROM scores
                WHERE seed=? AND mode=? AND rules=?
                ORDER BY score DESC, completed ASC, id ASC LIMIT 10''',
                ('' if seed is None else str(seed), mode, rules)).fetchall()
            return [dict(player=p, score=s, completed=d, id=i, material_left=m, swaps=w, stirs=t)
                    for p, s, d, i, m, w, t in rows]
        except sqlite3.Error as error:
            self._failed(error)
            return []

    def record(self, run_id, player, score, seed=None, mode=MODE, rules=RULES,
               *, material_left=None, swaps=None, stirs=None):
        if self.connection is None:
            return False
        if type(score) is not int or score < 0:
            raise ValueError('Score must be a nonnegative integer')
        for value in (material_left, swaps, stirs):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Efficiency statistics must be nonnegative integers or None')
        player = clean_player(player)
        try:
            with self.connection:
                self.connection.execute('''INSERT OR IGNORE INTO scores
                    (id, player, score, completed, mode, rules, seed, material_left, swaps, stirs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (run_id, player, score, datetime.now(timezone.utc).isoformat(), mode, rules,
                     '' if seed is None else str(seed), material_left, swaps, stirs))
            return True
        except sqlite3.Error as error:
            self._failed(error)
            return False
