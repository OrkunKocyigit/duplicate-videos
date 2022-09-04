import argparse
import concurrent.futures
import json
import os
import pathlib
import typing

import jsonpickle
import magic
import videohash


class VideoFile:
    def __init__(self, path: pathlib.Path) -> None:
        self.path: pathlib.Path = path
        self.hash: typing.Union[videohash.VideoHash, None] = None

    def __str__(self) -> str:
        return json.dumps(self.__getstate__())

    def __repr__(self) -> str:
        return self.__str__()

    def __getstate__(self):
        return {
            'path': self.path.as_posix(),
            'hash': "" if self.hash is None else self.hash.hash_hex
        }


def valid_directory_path(arg: str) -> pathlib.Path:
    path = pathlib.Path(arg).absolute()
    if path.is_dir():
        return path
    raise argparse.ArgumentTypeError("Invalid directory path")


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="duplicate-videos",
        description="Finds duplicate videos for given path",
    )
    parser.add_argument(
        "path",
        type=valid_directory_path
    )
    return parser


def is_video_file(file_path: pathlib.Path) -> bool:
    mime = magic.from_buffer(open(str(file_path), 'rb').read(2048), mime=True)
    return 'video/' in mime


def create_video_file_list(values: argparse.Namespace) -> list[VideoFile]:
    path = values.path
    result = []
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            file_path = pathlib.Path(dirpath, filename).absolute()
            if is_video_file(file_path):
                result.append(VideoFile(file_path))
        break
    return result


def calculate_video_hash(video_file: VideoFile) -> None:
    video_hash = videohash.VideoHash(path=str(video_file.path))
    video_file.hash = video_hash
    video_hash.delete_storage_path()


def calculate_hashes(video_files: list[VideoFile]) -> None:
    with concurrent.futures.ThreadPoolExecutor() as pool:
        pool.map(calculate_video_hash, video_files)


def find_duplicates(
        video_files: list[VideoFile]
) -> list[tuple[VideoFile, VideoFile]]:
    result = []
    for video_file in video_files:
        for video_file_dupe in video_files:
            if not video_file.path.samefile(
                    video_file_dupe.path) and video_file.hash.is_similar(
                    video_file_dupe.hash):
                result.append((video_file, video_file_dupe))
    return result


def save_file(file_name: str, obj: typing.Any) -> None:
    json_str = jsonpickle.encode(obj, unpicklable=False)
    with open(file_name, "w") as file:
        file.write(json_str)


def run():
    arg_parser = create_argument_parser()
    values = arg_parser.parse_args()
    video_files = create_video_file_list(values)
    calculate_hashes(video_files)
    save_file('videos.json', video_files)
    duplicate_files = find_duplicates(video_files)
    save_file('duplicates.json', duplicate_files)


if __name__ == '__main__':
    run()
