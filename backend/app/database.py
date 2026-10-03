from contextlib import contextmanager
from pathlib import Path
import sqlite3

class Database:
    def __init__(self, directory: Path):
        self.directory = directory
        self.path = directory / 'study.db'
        self.uploads = directory / 'uploads'

    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA busy_timeout=10000')
        return conn

    @contextmanager
    def session(self):
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        self.uploads.mkdir(parents=True, exist_ok=True)
        with self.session() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY)')
            conn.commit()
            for path in sorted((Path(__file__).resolve().parents[1] / 'migrations').glob('*.sql')):
                # SQLite permits only one writer. Lock before deciding which migrations to apply.
                conn.execute('BEGIN IMMEDIATE')
                if conn.execute('SELECT 1 FROM schema_migrations WHERE version=?', (path.name,)).fetchone():
                    conn.commit()
                    continue
                for statement in path.read_text(encoding='utf-8').split(';'):
                    if statement.strip():
                        conn.execute(statement)
                conn.execute('INSERT INTO schema_migrations VALUES (?)', (path.name,))
                conn.commit()
            # Background tasks are in-process: interrupted work needs an explicit retry.
            conn.execute("UPDATE documents SET status='failed', error_code='PROCESSING_INTERRUPTED' WHERE status IN ('pending','processing')")
