"""Local workflow persistence. One connection per operation; all updates are atomic."""
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException

DB_PATH = Path(os.getenv('MSL_WORKFLOW_DB', str(Path(__file__).parent / 'database' / 'workflow.sqlite3')))

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize():
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, parent_id TEXT REFERENCES sessions(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS session_versions(session_id TEXT REFERENCES sessions(id), revision INTEGER, saved_at TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(session_id,revision));
        CREATE TABLE IF NOT EXISTS interactions(id TEXT PRIMARY KEY, prepare_id TEXT REFERENCES sessions(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS questions(id TEXT PRIMARY KEY, interaction_id TEXT REFERENCES interactions(id), prepare_id TEXT REFERENCES sessions(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, payload TEXT NOT NULL);
        ''')

def get_session(identifier, revision=None):
    with connect() as db:
        if revision is None:
            row = db.execute('SELECT payload FROM sessions WHERE id=?', (identifier,)).fetchone()
        else:
            row = db.execute('SELECT payload FROM session_versions WHERE session_id=? AND revision=?', (identifier, revision)).fetchone()
    if not row:
        raise HTTPException(404, 'Prepare session not found')
    return json.loads(row['payload'])

def create_session(payload, parent_id=None):
    if parent_id:
        get_session(parent_id)
    timestamp = now()
    record = {**payload, 'id': str(uuid.uuid4()), 'parent_id': parent_id, 'created_at': timestamp, 'updated_at': timestamp, 'revision': 1}
    raw = json.dumps(record, ensure_ascii=False)
    with connect() as db:
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)', (record['id'], parent_id, timestamp, timestamp, 1, raw))
        db.execute('INSERT INTO session_versions VALUES(?,?,?,?)', (record['id'], 1, timestamp, raw))
    return record

def update_session(identifier, changes, revision):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload,revision FROM sessions WHERE id=?', (identifier,)).fetchone()
        if not row:
            raise HTTPException(404, 'Prepare session not found')
        if row['revision'] != revision:
            raise HTTPException(409, 'Session changed in another tab. Reopen the saved session before editing.')
        record = {**json.loads(row['payload']), **changes, 'updated_at': now(), 'revision': revision + 1}
        raw = json.dumps(record, ensure_ascii=False)
        db.execute('UPDATE sessions SET payload=?,revision=?,updated_at=? WHERE id=?', (raw, revision + 1, record['updated_at'], identifier))
        db.execute('INSERT INTO session_versions VALUES(?,?,?,?)', (identifier, revision + 1, record['updated_at'], raw))
    return record

TABLES = {'interactions', 'questions', 'tasks'}

def list_records(table):
    if table not in TABLES | {'sessions'}:
        raise ValueError('Unknown table')
    with connect() as db:
        return [json.loads(row['payload']) for row in db.execute(f'SELECT payload FROM {table} ORDER BY created_at DESC')]

def get_record(table, identifier):
    if table not in TABLES:
        raise ValueError('Unknown table')
    with connect() as db:
        row = db.execute(f'SELECT payload FROM {table} WHERE id=?', (identifier,)).fetchone()
    if not row:
        raise HTTPException(404, 'Record not found')
    return json.loads(row['payload'])

def save_record(table, payload, identifier=None):
    if table not in TABLES:
        raise ValueError('Unknown table')
    old = get_record(table, identifier) if identifier else {}
    record = {**old, **payload, 'id': identifier or str(uuid.uuid4()), 'created_at': old.get('created_at', now()), 'updated_at': now()}
    raw = json.dumps(record, ensure_ascii=False)
    with connect() as db:
        if table == 'tasks':
            db.execute('INSERT OR REPLACE INTO tasks VALUES(?,?,?)', (record['id'], record['created_at'], raw))
        elif table == 'interactions':
            db.execute('INSERT OR REPLACE INTO interactions VALUES(?,?,?,?,?)', (record['id'], record.get('prepare_id'), record['created_at'], record['updated_at'], raw))
        else:
            db.execute('INSERT OR REPLACE INTO questions VALUES(?,?,?,?,?,?)', (record['id'], record.get('interaction_id'), record.get('prepare_id'), record['created_at'], record['updated_at'], raw))
    return record

def setting(key, value=None):
    with connect() as db:
        if value is not None:
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (key, json.dumps(value, ensure_ascii=False)))
        row = db.execute('SELECT payload FROM settings WHERE key=?', (key,)).fetchone()
    return json.loads(row['payload']) if row else None

initialize()
