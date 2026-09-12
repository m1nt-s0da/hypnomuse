import os
from hashlib import sha256
from ._db import open_lancedb, LanceDBTextCache, open_sqlite
from .scan._model import get_processor, get_model
import torch
from uuid import uuid7, UUID
from dataclasses import dataclass
import math
from typing import cast
from transformers.modeling_outputs import BaseModelOutputWithPooling


def encode_query(query: str, data_dir: str) -> list[float]:
    query_hash = sha256(query.encode("utf-8")).hexdigest()
    with open_lancedb(data_dir) as lancedb:
        text_cache_table = lancedb.open_table("text_cache")
        response = (
            text_cache_table.search()
            .where(f"sha256 = '{query_hash}'")
            .limit(1)
            .to_list()
        )
        if response:
            return response[0]["vector"]

    model = get_model()
    processor = get_processor()
    inputs = processor(
        text=[query],
        return_tensors="pt",  # type: ignore[reportCallIssue]
        padding=True,  # type: ignore[reportCallIssue]
    )
    with torch.no_grad():
        model_output = cast(
            BaseModelOutputWithPooling, model.get_text_features(**inputs)
        )
        vector_tensor = cast(torch.Tensor, model_output.pooler_output)
        norm = torch.linalg.norm(vector_tensor)
        if norm > 0:
            vector_tensor = vector_tensor / norm

        vector = vector_tensor.squeeze(0).cpu().tolist()

        with open_lancedb(data_dir) as lancedb:
            text_cache_table = lancedb.open_table("text_cache")
            text_cache_table.add(
                [
                    LanceDBTextCache(
                        sha256=query_hash,
                        vector=vector,
                    )
                ]
            )

        return vector


@dataclass
class FoundTrack:
    id: UUID
    title: str
    artist: str
    album: str
    distance: float
    confidence: float


def search_tracks(
    query: str, data_dir: str, *, count=10, confidence_gamma: float = 2.0
):
    query_vector = encode_query(query, data_dir)
    with open_lancedb(data_dir) as lancedb:
        track_table = lancedb.open_table("tracks")
        candidate_tracks = (
            track_table.search(query_vector)
            .select(["id", "_distance"])
            .limit(count)
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
                    [(UUID(result["id"]).bytes,) for result in candidate_tracks],
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

    return [
        FoundTrack(
            id=UUID(result["id"]),
            title=track_dict[UUID(result["id"])]["title"],
            artist=track_dict[UUID(result["id"])]["artist"],
            album=track_dict[UUID(result["id"])]["album"],
            distance=result["_distance"],
            confidence=math.exp(-confidence_gamma * result["_distance"]),
        )
        for result in candidate_tracks
    ]


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Search tracks by query")
    parser.add_argument("query", type=str)
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Directory to store data",
        default=os.environ.get("HYPNOMUSE_DATA_DIR"),
        required=os.environ.get("HYPNOMUSE_DATA_DIR") is None,
    )
    args = parser.parse_args()
    print(f"Query: {args.query}")
    result = search_tracks(**vars(args))
    for track in result:
        print(
            f"{track.confidence*100:06.2f}% ({track.distance:.2f}) {track.id}: {track.title} / {track.artist} / {track.album}"
        )
