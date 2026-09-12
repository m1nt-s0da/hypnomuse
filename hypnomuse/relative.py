from ._db import open_sqlite, open_lancedb
import os
from uuid import UUID, uuid7
from dataclasses import dataclass
import math


@dataclass
class RelativeTrackQuery:
    id: UUID
    title: str
    artist: str
    album: str


@dataclass
class RelativeTrack(RelativeTrackQuery):
    distance: float
    confidence: float


@dataclass
class RelativeTrackResponse:
    query: RelativeTrackQuery
    relatives: list[RelativeTrack]


def find_relative_track(
    track_id: UUID, data_dir: str, *, count=10, confidence_gamma: float = 2.0
):
    with open_lancedb(data_dir) as lancedb:
        track_table = lancedb.open_table("tracks")
        response = track_table.search().where(f"id = '{track_id}'").limit(1).to_list()
        if not response:
            raise ValueError(f"Track with ID {track_id} not found")

        [result] = response
        query_vector = result["vector"]

        results = (
            track_table.search(query_vector)
            .select(["id", "_distance"])
            .limit(count + 1)
            .to_list()
        )

        with open_sqlite(data_dir, readonly=True) as sqlite:
            table_uuid = uuid7().hex
            sqlite.execute(
                f"CREATE TEMPORARY TABLE find_track_ids_{table_uuid} (id BLOB PRIMARY KEY NOT NULL) WITHOUT ROWID;"
            )
            sqlite.executemany(
                f"INSERT INTO find_track_ids_{table_uuid} (id) VALUES (?)",
                list(
                    set(
                        [
                            (track_id.bytes,),
                            *[(UUID(result["id"]).bytes,) for result in results],
                        ]
                    )
                ),
            )
            cur = sqlite.execute(
                f"SELECT id, title, artist, album FROM tracks WHERE id IN (SELECT id FROM find_track_ids_{table_uuid});"
            )
            track_rows = cur.fetchall()
        track_dict = {
            UUID(bytes=row[0]): {
                "id": UUID(bytes=row[0]),
                "title": row[1],
                "artist": row[2],
                "album": row[3],
            }
            for row in track_rows
        }

        return RelativeTrackResponse(
            query=RelativeTrackQuery(
                id=track_id,
                title=track_dict[track_id]["title"],
                artist=track_dict[track_id]["artist"],
                album=track_dict[track_id]["album"],
            ),
            relatives=[
                RelativeTrack(
                    id=UUID(result["id"]),
                    title=track_dict[UUID(result["id"])]["title"],
                    artist=track_dict[UUID(result["id"])]["artist"],
                    album=track_dict[UUID(result["id"])]["album"],
                    distance=result["_distance"],
                    confidence=math.exp(-confidence_gamma * result["_distance"]),
                )
                for result in results
                if UUID(result["id"]) != track_id
            ],
        )


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Find a track by its ID")
    parser.add_argument("track_id", type=UUID)
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store data",
        default=os.environ.get("HYPNOMUSE_DATA_DIR"),
        required=os.environ.get("HYPNOMUSE_DATA_DIR") is None,
    )
    args = parser.parse_args()
    print(args)
    result = find_relative_track(**vars(args))
    print(
        f"Query track {result.query.id}: {result.query.title} / {result.query.artist} / {result.query.album}"
    )
    print(f"Relatives:")
    for relative in result.relatives:
        print(
            f"{relative.confidence*100:06.2f}% ({relative.distance:.2f}) {relative.id}: {relative.title} / {relative.artist} / {relative.album}"
        )
