import sqlite3
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db() -> None:
    with current_app.open_resource('schema.sql') as f:
        get_db().executescript(f.read().decode('utf-8'))
