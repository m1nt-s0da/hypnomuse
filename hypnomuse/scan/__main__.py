from argparse import ArgumentParser
from logging import getLogger
from glob import glob as glob_files
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import os
from ._register_file import register_file

logger = getLogger(__name__)


def main(glob: list[str], ext: list[str], data_dir: str):
    logger.info(f"Starting scan: {glob} ({ext})")
    found_files: list[str] = []
    for pattern in glob:
        for file in glob_files(pattern):
            if any(file.endswith(f".{e}") for e in ext):
                found_files.append(file)
    logger.info(f"Found {len(found_files)} files.")
    with logging_redirect_tqdm():
        for file in tqdm(found_files, desc="Processing files"):
            file = os.path.abspath(file)
            # logger.info(f"Processing file: {file}")
            register_file(file, data_dir)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("glob", type=str, help="Glob pattern to match files", nargs="+")
    parser.add_argument(
        "--ext",
        "-e",
        type=str,
        help="File extension to filter by",
        nargs="+",
        default=["wav", "mp3", "ogg", "flac", "m4a", "aac"],
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
    main(**vars(args))
