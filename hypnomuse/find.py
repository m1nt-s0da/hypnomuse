from ._db import open_sqlite
import os
from uuid import UUID


def find_track(
    *,
    title: str | None = None,
    artist: str | None = None,
    album: str | None = None,
    free_text: str | None = None,
    data_dir: str,
):
    title = f"%{title}%" if title is not None else "%"
    artist = f"%{artist}%" if artist is not None else "%"
    album = f"%{album}%" if album is not None else "%"
    free_text = f"%{free_text}%" if free_text is not None else "%"

    with open_sqlite(data_dir) as conn:
        cur = conn.execute(
            "SELECT id, title, artist, album FROM tracks WHERE title LIKE ? AND artist LIKE ? AND album LIKE ? AND (title LIKE ? OR artist LIKE ? OR album LIKE ?) ORDER BY id LIMIT 10",
            (title, artist, album, free_text, free_text, free_text),
        )
        items = cur.fetchall()
        if len(items) == 0:
            print("No tracks found.")
            return
        for id, title, artist, album in items:
            id = UUID(bytes=id)
            print(f"{id}: {title} / {artist} / {album}")


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Find a track by title, artist, and album")
    parser.add_argument("--title", type=str, help="Title of the track")
    parser.add_argument("--artist", type=str, help="Artist of the track")
    parser.add_argument("--album", type=str, help="Album of the track")
    parser.add_argument(
        "free_text", type=str, help="Free text search for the track", nargs="?"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store data",
        default=os.environ.get("HYPNOMUSE_DATA_DIR"),
        required=os.environ.get("HYPNOMUSE_DATA_DIR") is None,
    )
    args = parser.parse_args()
    print(args)
    tracks = find_track(**vars(args))
