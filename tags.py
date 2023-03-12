from typing import Iterable
import os
from builtins import set as bset
import files
from pathlib import Path
import re


NAME_TAGS_SUFFIX_RE = re.compile("^(.*)(\[.*?\])(\.\w+)?$")
NAME_SUFFIX_RE = re.compile("^(.*?)(\.\w+)?$")


def remove_forbidden_chars(name: str, name_only=False):
    """ Variant of files.remove_forbidden_chars that also removes square brackets, intended to be used on files that are known not to have any tags. """
    name = files.remove_forbidden_chars(name, name_only)
    for c in ["[", "]"]:
        name = name.replace(c, "")
    return name


def name_and_suffix(filename: str) -> tuple[str, str]:
    match = NAME_TAGS_SUFFIX_RE.match(filename)
    if match:
        name = match.group(1)
        ext = match.group(3)
    else:
        match = NAME_SUFFIX_RE.match(filename)
        name = match.group(1)
        ext = match.group(2)
    # ext can be None
    return (name, ext if ext else "")


def name(filename: str) -> str:
    match = NAME_TAGS_SUFFIX_RE.match(filename)
    if match:
        return match.group(1)
    match = NAME_SUFFIX_RE.match(filename)
    return match.group(1)


def suffix(filename: str) -> str:
    """ Differs from Path.suffix by starting the suffix with the LAST . character, not the first. """
    match = NAME_TAGS_SUFFIX_RE.match(filename)
    if match:
        return match.group(3)
    match = NAME_SUFFIX_RE.match(filename)
    return match.group(2) or ""


def __remove_whitespace(tags: Iterable[str]) -> bset[str]:
    """ Removes leading and trailing whitespace and removes tags that are entirely whitespace. """
    return {t.strip() for t in tags if not re.match("^\s*$", t)}


def set(filename: str, tags: Iterable[str]) -> str:
    tags = sorted(__remove_whitespace(tags))
    name, suffix = name_and_suffix(filename)
    if len(tags) == 0:
        return name + suffix
    return name + "[" + " ".join(tags) + "]" + suffix


def get(filename: str) -> bset[str]:
    match = NAME_TAGS_SUFFIX_RE.match(filename)
    if not match:
        return bset()
    tags_str = match.group(2)
    if tags_str == None:
        return bset()
    else:
        # remove []
        tags_str = tags_str[1:-1]
        return bset(re.split("\s+", tags_str))


def add(filename: str, new_tags: Iterable[str]) -> str:
    return set(filename, get(filename) | bset(new_tags))


def remove(filename: str, remove_tags: Iterable[str]) -> str:
    return set(filename, get(filename) - bset(remove_tags))


def rename(filename: str, new_name: str) -> str:
    return new_name + filename[len(name(filename)):]


def matching_files(root: os.PathLike, pattern: str = None, include_tags: Iterable[str] = None, exclude_tags: Iterable[str] = None, recursive: bool = True) -> Iterable[Path]:
    """ All include_tags must be present, and none of the exclude_tags. (To get files with some tags OR some other ones, just do another search.) """
    if include_tags is not None:
        include_tags = bset(include_tags)
    if exclude_tags is not None:
        exclude_tags = bset(exclude_tags)

    file_list = []

    def file_action(f: Path, d: int):
        matches_pattern = pattern is None or re.search(pattern, name(f.name))
        file_tags = get(f.name)
        matches_include_tags = include_tags is None or file_tags > include_tags
        matches_exclude_tags = exclude_tags is not None and (
            file_tags & exclude_tags)
        if matches_pattern and matches_include_tags and not matches_exclude_tags:
            file_list.append(f)

    def skip_dir(f: Path, d: int):
        # still go over the top-level folder's contents if not recursive
        return not recursive and d > 0

    files.walk(root, file_action=file_action, skip_dir=skip_dir)

    return file_list


def tag_in_folder(root: os.PathLike, tags: Iterable[str] = [], *, pattern: str = None, match_include_tags: Iterable[str] = None, match_exclude_tags: Iterable[str] = None, recursive: bool = True, remove_tags=[]) -> None:
    """ Adds/removes the tags to each file in the root folder if its name matches the regular expression pattern and/or set of match tags (the default None parameters match anything). """
    tags = bset(tags)
    planned_moves = {}

    for f in matching_files(root, pattern, match_include_tags, match_exclude_tags, recursive):
        new_name = remove(add(f.name, tags), remove_tags)
        if f.name != new_name:
            planned_moves[f] = f.with_name(new_name)

    files.move_by_dict(planned_moves)


def collect(root: os.PathLike) -> bset[str]:
    """ Returns all of the tags on files in this folder, along with counts. """
    collected_tags = {}

    def file_action(f: Path, d: int):
        for t in get(f.name):
            collected_tags[t] = collected_tags.get(t, 0) + 1

    files.walk(root, file_action=file_action)

    return collected_tags


def map_to_folders(root: os.PathLike, tags: Iterable[str]) -> dict[str, bset[Path]]:
    """ Match each tag to a folder with the tag in its name (as a space-separated list).  """
    tags = bset(tags)
    tags_to_folders: dict[str, bset] = {}

    def dir_action(f: Path, d: int):
        tags_in_name = __remove_whitespace(f.name.split())
        for t in tags & tags_in_name:
            if not t in tags_to_folders:
                tags_to_folders[t] = bset()
            tags_to_folders[t].add(f)

    files.walk(root, dir_action=dir_action)

    return tags_to_folders


def tag_by_folder(root: os.PathLike):
    """ For each subfolder of the root, tags all the files inside with the tags in the subfolder name (as a space-separated list). """

    root = Path(root)
    planned_moves = {}

    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        tags = folder.stem.split()
        for file in folder.iterdir():
            if not file.is_file():
                continue
            new_name = add(file.name, tags)
            if file.name != new_name:
                planned_moves[file] = file.with_name(new_name)

    files.move_by_dict(planned_moves)


if __name__ == "__main__":
    result = name_and_suffix("file.txt")
    assert result == ("file", ".txt"), result
    result = name_and_suffix("file[tag1].txt")
    assert result == ("file", ".txt"), result
    result = name_and_suffix("file[tag1 tag2].txt")
    assert result == ("file", ".txt"), result
    result = name_and_suffix("asdf")
    assert result == ("asdf", ""), result
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
