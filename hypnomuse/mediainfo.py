import mutagen
import mutagen.id3
import mutagen.mp4
import mutagen.oggvorbis
import chardet


def decode_str(
    text: bytes,
    *,
    default_encoding: str = "utf-8",
    include_encodings: list[str] | None = ["utf-8", "cp932", "EUC-JP"],
):
    detect = chardet.detect(text, include_encodings=include_encodings)
    encoding = detect["encoding"]
    if encoding is None:
        encoding = default_encoding
    if encoding.lower() == "shift_jis":
        encoding = "cp932"

    try:
        return text.decode(encoding)
    except UnicodeDecodeError:
        return text.decode(default_encoding, errors="replace")


def get_mediainfo(file: str):
    audio = mutagen.File(file)
    if audio is None:
        raise ValueError("Unable to read media file")

    raw_tags: dict[str, bytes | None] = {"title": None, "artist": None, "album": None}

    # -------------------------------------------------------------
    # 1. MP3 / WAV (ID3v2 タグ) の場合
    # -------------------------------------------------------------
    id3 = audio if isinstance(audio, mutagen.id3.ID3) else getattr(audio, "tags", None)
    if isinstance(id3, mutagen.id3.ID3):

        # ID3フレーム ID: TIT2(タイトル), TPE1(アーティスト), TALB(アルバム)
        frame_map = {"title": "TIT2", "artist": "TPE1", "album": "TALB"}

        for key, frame_id in frame_map.items():
            frame = id3.get(frame_id)
            if frame:
                # 文字列として読まれている場合、ISO-8859-1 (Latin-1) でエンコードし直して元のバイト列を復元
                text_val = str(frame.text[0])
                try:
                    raw_tags[key] = text_val.encode("iso-8859-1")
                except UnicodeEncodeError:
                    raw_tags[key] = text_val.encode("utf-8")

    # -------------------------------------------------------------
    # 2. M4A / AAC (MP4 アトム) の場合
    # -------------------------------------------------------------
    elif isinstance(audio, mutagen.mp4.MP4):
        # MP4アトムキー: '\xa9nam'(タイトル), '\xa9ART'(アーティスト), '\xa9alb'(アルバム)
        atom_map = {"title": "\xa9nam", "artist": "\xa9ART", "album": "\xa9alb"}

        for key, atom_id in atom_map.items():
            val_list = audio.get(atom_id)
            if val_list:
                val = val_list[0]
                if isinstance(val, bytes):
                    raw_tags[key] = val
                elif isinstance(val, str):
                    try:
                        raw_tags[key] = val.encode("iso-8859-1")
                    except UnicodeEncodeError:
                        raw_tags[key] = val.encode("utf-8")

    # -------------------------------------------------------------
    # 3. OGG (Vorbis Comment) の場合
    # -------------------------------------------------------------
    elif isinstance(audio, mutagen.oggvorbis.OggVorbis):
        # Vorbis Comment キー: TITLE, ARTIST, ALBUM (大文字)
        ogg_map = {"title": "TITLE", "artist": "ARTIST", "album": "ALBUM"}

        for key, ogg_id in ogg_map.items():
            val_list = audio.get(ogg_id)
            if val_list:
                val = val_list[0]
                try:
                    raw_tags[key] = val.encode("iso-8859-1")
                except UnicodeEncodeError:
                    raw_tags[key] = val.encode("utf-8")

    raw_title = raw_tags.get("title")
    raw_artist = raw_tags.get("artist")
    raw_album = raw_tags.get("album")

    return {
        "title": decode_str(raw_title) if raw_title is not None else None,
        "artist": decode_str(raw_artist) if raw_artist is not None else None,
        "album": decode_str(raw_album) if raw_album is not None else None,
    }


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Get media info for a file")
    parser.add_argument("file", type=str, help="Path to the media file")
    args = parser.parse_args()
    info = get_mediainfo(args.file)
    print(info)
