from .._db import open_sqlite, open_lancedb, LanceDBTrack
import os
from hashlib import sha256
from logging import getLogger
from ._scan_audio import scan_audio
from uuid import uuid7, UUID
from ..mediainfo import get_mediainfo

__all__ = ["register_file"]

logger = getLogger(__name__)


def register_file(file: str, data_dir: str):
    with open_sqlite(data_dir) as conn:
        stat = os.stat(file)
        st_mtime_ns = stat.st_mtime_ns
        cur = conn.execute(
            "SELECT id FROM files WHERE path = ? AND st_mtime_ns = ?",
            (file, st_mtime_ns),
        )
        row = cur.fetchone()
        if row is not None:
            return

        hash = sha256()
        with open(file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash.update(chunk)
        hash = hash.digest()

        cur = conn.execute(
            "SELECT id FROM tracks WHERE sha256 = ?",
            (hash,),
        )
        row = cur.fetchone()
        if row is not None:
            track_id = row[0]
            conn.execute(
                "INSERT INTO files (track_id, path, st_mtime_ns) VALUES (?, ?, ?);",
                (track_id, file, st_mtime_ns),
            )
            return

        # トラック情報がない場合、トラックをスキャンする
        logger.info(f"Scanning track for file: {file}")
        tag = get_mediainfo(file)
        title = tag["title"] or os.path.basename(file)
        artist = tag["artist"]
        album = tag["album"]

        title = title.decode("utf-8") if isinstance(title, bytes) else title
        artist = artist.decode("utf-8") if isinstance(artist, bytes) else artist
        album = album.decode("utf-8") if isinstance(album, bytes) else album

        embeddings = scan_audio(file)

        track_id = uuid7()
        conn.execute(
            "INSERT INTO tracks (id, sha256, title, artist, album) VALUES (?, ?, ?, ?, ?);",
            (track_id.bytes, hash, title, artist, album),
        )

        file_id = uuid7()
        conn.execute(
            "INSERT INTO files (id, track_id, path, st_mtime_ns) VALUES (?, ?, ?, ?);",
            (file_id.bytes, track_id.bytes, file, st_mtime_ns),
        )

        with open_lancedb(data_dir) as db:
            table = db.open_table("tracks")
            table.add(
                [
                    LanceDBTrack(
                        id=str(track_id),
                        vector=embeddings,
                        title=title,
                        artist=artist,
                        album=album,
                    )
                ]
            )
