import typing
import os
from builtins import set as bset
from mypy import files
from pathlib import Path
import re


class TagException(Exception):
    pass


def name_and_ext(filename: str) -> tuple[str, str]:
    match = re.match("(.*?)(\[.*\])?(\..*)", filename)
    if not match:
        raise TagException("Filename was not of correct format")
    name = match.group(1)
    ext = match.group(3)
    return (name, ext)


def add(filename: str, new_tags: typing.Iterable[str]) -> str:
    return set(filename, get(filename) | bset(new_tags))


def remove(filename: str, remove_tags: typing.Iterable[str]) -> str:
    return set(filename, get(filename) - bset(remove_tags))


def get(filename: str) -> bset[str]:
    match = re.match("(.*?)(\[.*\])?\.(.*)", filename)
    if not match:
        raise TagException("Filename was not in correct format")
    tags = match.group(2)
    if tags == None:
        return bset()
    else:
        # remove []
        tags = tags[1:-1]
        tags = re.split("\s+", tags)
        return bset(tags)


def set_name(filename: str, new_name: str) -> str:
    name, _ = name_and_ext(filename)
    return new_name + filename[len(name):]


def tag_all_in(root: os.PathLike, tags: typing.Iterable[str], *, visit_subdirs: bool = True, remove_tags=False) -> None:
    tags = bset(tags)
    planned_moves = {}

    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if remove_tags:
                new_name = remove(f, tags)
            else:
                new_name = add(f, tags)
            if f != new_name:
                planned_moves[Path(dirpath, f)] = Path(dirpath, new_name)
        if not visit_subdirs:
            break

    files.move_by_dict(planned_moves)


def collect(root: os.PathLike) -> bset[str]:
    collected_tags = bset()
    for _, _, filenames in os.walk(root):
        for f in filenames:
            collected_tags |= get(f)
    return collected_tags


def map_to_folders(root: os.PathLike, tags: typing.Iterable[str]) -> dict[str, bset[os.PathLike]]:
    tags_to_folders = {}
    for dirpath, dirnames, _ in os.walk(root):
        for d in dirnames:
            for t in tags:
                if t in d:
                    if t not in tags_to_folders:
                        tags_to_folders[t] = bset()
                    tags_to_folders[t].add(Path(dirpath, d))
    return tags_to_folders


def set(filename: str, tags: typing.Iterable[str]) -> str:
    tags = bset(tags)
    if "" in tags:
        tags.remove("")
    name, ext = name_and_ext(filename)
    if len(tags) == 0:
        return name + ext
    return name + "[" + " ".join([t.strip() for t in sorted(tags)]) + "]" + ext


if __name__ == "__main__":
    result = name_and_ext("file.txt")
    assert result == ("file", ".txt"), result
    result = name_and_ext("file[tag1].txt")
    assert result == ("file", ".txt"), result
    result = name_and_ext("file[tag1 tag2].txt")
    assert result == ("file", ".txt"), result
    try:
        name_and_ext("asdf")
        assert False, "expected this to fail"
    except TagException:
        pass

    result = get("file.txt")
    assert result == bset(), result
    result = get("file[tag1].txt")
    assert result == {"tag1"}, result
    result = get("file[tag1      tag2].txt")
    assert result == {"tag1", "tag2"}, result

    result = add("file.txt", ["tag1", "tag2"])
    assert result == "file[tag1 tag2].txt", result
    result = add("file[tag3].txt", ["tag1              ", "tag2"])
    assert result == "file[tag1 tag2 tag3].txt", result
    result = remove("file.txt", ["tag1", "tag2"])
    assert result == "file.txt", result
    result = remove("file[tag1 tag2].txt", ["tag1", "tag2"])
    assert result == "file.txt", result
    result = remove("file[tag3].txt", ["tag1", "tag2"])
    assert result == "file[tag3].txt", result
