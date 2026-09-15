import os
from hashlib import sha256
from ._db import open_lancedb, open_sqlite
from uuid import uuid7, UUID
from dataclasses import dataclass
import math
from typing import cast
from slopmachine.embedding.ruri_v3_130m_int8 import RuriV3_130M_Int8
import onnxruntime as ort
import numpy as np
import asyncio

projection_onnx_file = os.path.dirname(__file__) + "/ruri-clap-projection.onnx"


async def encode_query(query: str) -> list[float]:
    # if len(query) < 10:
    #     query = f"{query}の雰囲気を持つ音楽や楽曲"
    ruri = RuriV3_130M_Int8()
    tokens = await ruri.tokenize([f"クエリ: {query}"])
    ruri_embeds = await ruri.encode(tokens.input_ids, tokens.attention_mask)

    session = ort.InferenceSession(projection_onnx_file)
    model_input = session.get_inputs()[0]
    model_output = session.get_outputs()[0]
    [projected_embeds] = cast(
        np.ndarray,
        session.run(
            [model_output.name],
            {model_input.name: np.asarray(ruri_embeds, dtype=np.float32)},
        )[0],
    )
    projected_embeds = projected_embeds / np.linalg.norm(projected_embeds)

    return projected_embeds.tolist()


@dataclass
class FoundTrack:
    id: UUID
    title: str
    artist: str
    album: str
    distance: float
    confidence: float


async def search_tracks(
    query: str, data_dir: str, *, count=10, confidence_gamma: float = 2.0
):
    query_vector = await encode_query(query)
    with open_lancedb(data_dir) as lancedb:
        track_table = lancedb.open_table("tracks")
        candidate_tracks = (
            track_table.search(query_vector)
            .metric("dot")
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
    result = asyncio.run(search_tracks(**vars(args)))
    for track in result:
        print(
            f"{track.confidence*100:06.2f}% ({track.distance:.2f}) {track.id}: {track.title} / {track.artist} / {track.album}"
        )
