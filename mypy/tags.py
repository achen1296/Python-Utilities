import typing
import os
from builtins import set as bset
from mypy import files
from pathlib import Path


def name_and_ext(filename: str) -> tuple[str, str]:
    lbr = filename.rfind("[")
    rbr = filename.rfind("]")
    if rbr != -1 and lbr != -1 and lbr < rbr:
        # existing tags
        name = filename[:lbr]
        ext = filename[rbr + 1:]
    else:
        # no existing tags
        dot = filename.rfind(".")
        name = filename[:dot]
        ext = filename[dot:]
    return (name, ext)


def add(filename: str, new_tags: typing.Iterable[str]) -> str:
    return set(filename, get(filename) | bset(new_tags))


def remove(filename: str, remove_tags: typing.Iterable[str]) -> str:
    return set(filename, get(filename) - bset(remove_tags))


def get(filename: str) -> bset[str]:
    lbr = filename.rfind("[")
    rbr = filename.rfind("]")
    tags = bset()
    if rbr != -1 and lbr != -1 and lbr < rbr:
        for tag in filename[lbr + 1:rbr].split(" "):
            tag = tag.strip()
            if tag == "":
                continue
            tags.add(tag.lower())
    return tags


def set_name(filename: str, new_name: str) -> str:
    name, ext = name_and_ext(filename)
    return new_name + filename[len(name):]


def tag_all_in(root: os.PathLike, new_tags: typing.Iterable[str], visit_subdirs: bool = True) -> None:
    new_tags = bset(new_tags)
    planned_moves = {}

    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            new_name = add(f, new_tags)
            if f != new_name:
                planned_moves[dirpath + os.sep +
                              f] = dirpath + os.sep + new_name
        if not visit_subdirs:
            break

    files.move_by_dict(planned_moves)


def untag_all_in(root: os.PathLike, remove_tags: typing.Iterable[str], visit_subdirs: bool = True) -> None:
    remove_tags = bset(remove_tags)

    planned_moves = {}

    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            new_name = remove(f, remove_tags)
            if f != new_name:
                planned_moves[dirpath + os.sep +
                              f] = dirpath + os.sep + new_name
        if not visit_subdirs:
            break

    files.move_by_dict(planned_moves)


def collect(root: os.PathLike) -> bset[str]:
    collected_tags = bset()
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            collected_tags |= get(f)
    return collected_tags


def map_to_folders(root: os.PathLike, tags: typing.Iterable[str]) -> dict[str, bset[os.PathLike]]:
    tags_to_folders = {}
    for dirpath, dirnames, filenames in os.walk(root):
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
    tags_str = ""
    first = True
    for tag in sorted(tags):
        if first:
            first = False
        else:
            tags_str += " "
        tags_str += tag
    return name + "[" + tags_str + "]" + ext
