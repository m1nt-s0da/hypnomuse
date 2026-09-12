from sqlite3 import connect
import os
import lancedb
from lancedb.pydantic import LanceModel, Vector
from contextlib import contextmanager

__all__ = ["open_sqlite", "open_lancedb", "LanceDBTrack", "LanceDBTextCache"]


def open_sqlite(data_dir: str, readonly: bool = False):
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "database.sqlite3")

    if readonly:
        conn = connect(f"file:{db_path}?mode=ro", uri=True)
    else:
        conn = connect(f"file:{db_path}", uri=True)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    if readonly:
        return conn

    conn.execute(
        "CREATE TABLE IF NOT EXISTS tracks ("
        "id BLOB PRIMARY KEY NOT NULL, "
        "sha256 BLOB NOT NULL UNIQUE, "
        "title TEXT NOT NULL, "
        "artist TEXT NOT NULL, "
        "album TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ") WITHOUT ROWID;"
    )

    conn.execute(
        "CREATE TABLE IF NOT EXISTS files ("
        "id BLOB PRIMARY KEY NOT NULL, "
        "track_id BLOB NOT NULL, "
        "path TEXT NOT NULL, "
        "st_mtime_ns INTEGER NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
        "FOREIGN KEY(track_id) REFERENCES tracks(id) ON DELETE CASCADE, "
        "UNIQUE(path, st_mtime_ns) "
        ") WITHOUT ROWID;"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_track_id ON files(track_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_st_mtime_ns ON files(st_mtime_ns);"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_path_st_mtime_ns ON files(path, st_mtime_ns);"
    )
    return conn


class LanceDBTrack(LanceModel):
    id: str
    vector: Vector(512)  # type: ignore[reportInvalidTypeForm]
    title: str
    artist: str | None = None
    album: str | None = None


class LanceDBTextCache(LanceModel):
    sha256: str
    vector: Vector(512)  # type: ignore[reportInvalidTypeForm]


@contextmanager
def open_lancedb(data_dir: str):
    os.makedirs(data_dir, exist_ok=True)

    db = lancedb.connect(data_dir)
    if "tracks" not in db.table_names():
        db.create_table("tracks", schema=LanceDBTrack, data=None)
    if "text_cache" not in db.table_names():
        db.create_table("text_cache", schema=LanceDBTextCache, data=None)

    try:
        yield db
    finally:
        pass
