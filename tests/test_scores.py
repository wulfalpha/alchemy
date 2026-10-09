import sqlite3
from unittest.mock import patch

from alchemy.scores import Scoreboard, data_directory


def test_persistence_ranking_and_duplicate_submission(tmp_path):
    scores = Scoreboard(tmp_path)
    for n in range(12):
        assert scores.record(str(n), 'Ada', n*100)
    assert scores.record('11', 'Ada', 9999)
    scores.close()
    scores = Scoreboard(tmp_path)
    assert [row['score'] for row in scores.top()] == list(range(1100, 100, -100))
    scores.close()


def test_modes_rules_and_seeds_do_not_mix(tmp_path):
    scores = Scoreboard(tmp_path)
    for key, options in [('normal', {}), ('seed0', {'seed':0}), ('seed1', {'seed':1}),
                         ('future', {'mode':'reactants'}), ('old', {'rules':'old'})]:
        scores.record(key, key, 100, **options)
    assert [r['player'] for r in scores.top()] == ['normal']
    assert [r['player'] for r in scores.top(seed=0)] == ['seed0']
    assert [r['player'] for r in scores.top(seed=1)] == ['seed1']
    scores.close()


def test_corrupt_file_preserved(tmp_path):
    path = tmp_path / 'scores.sqlite3'
    path.write_bytes(b'broken database')
    scores = Scoreboard(tmp_path)
    assert scores.error
    assert scores.top() == []
    assert not scores.record('id', 'Player', 100)
    assert path.read_bytes() == b'broken database'


def test_missing_directory_created_and_name_cleaned(tmp_path):
    scores = Scoreboard(tmp_path / 'nested')
    scores.record('one', '  \n  ', 0)
    scores.record('two', 'A'*40, 100)
    assert [r['player'] for r in scores.top()] == ['A'*16, 'Alchemist']
    scores.close()


def test_unwritable_location_does_not_raise(tmp_path):
    path = tmp_path / 'file'
    path.write_text('keep')
    scores = Scoreboard(path)
    assert scores.error and scores.top() == []
    assert path.read_text() == 'keep'


def test_newer_schema_preserved(tmp_path):
    with sqlite3.connect(tmp_path / 'scores.sqlite3') as db:
        db.execute('PRAGMA user_version = 99')
    scores = Scoreboard(tmp_path)
    assert scores.error
    with sqlite3.connect(scores.path) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 99


def test_two_instances_keep_both_results(tmp_path):
    a, b = Scoreboard(tmp_path), Scoreboard(tmp_path)
    a.record('one', 'One', 100)
    b.record('two', 'Two', 200)
    assert len(a.top()) == 2
    a.close()
    b.close()


def test_platform_paths(monkeypatch, tmp_path):
    monkeypatch.delenv('ALCHEMY_DATA_DIR', raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    with patch('alchemy.scores.sys.platform', 'win32'):
        assert data_directory() == tmp_path / 'Alchemy'
    with patch('alchemy.scores.sys.platform', 'linux'):
        assert data_directory() == tmp_path / 'alchemy'


def test_player_name_remembered_without_changing_scores(tmp_path):
    scores = Scoreboard(tmp_path)
    assert scores.player() == 'Alchemist'
    scores.record('old', 'Old name', 100)
    assert scores.set_player('  Ada\n  ') == 'Ada'
    scores.close()
    scores = Scoreboard(tmp_path)
    assert scores.player() == 'Ada'
    assert scores.top()[0]['player'] == 'Old name'
    assert scores.set_player(' ') == 'Alchemist'
    scores.close()
