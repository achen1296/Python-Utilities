# (c) Andrew Chen (https://github.com/achen1296)

import re
from builtins import set as bset
from pathlib import Path
from typing import Callable, Iterable

import files
from booleans import BooleanExpression

FORBIDDEN_CHARS = "[]!&"


def remove_forbidden_chars(name: str, name_only=False):
    """ Variant of files.remove_forbidden_chars that also removes square brackets and ! and & (expression characters), intended to be used on file names that are known not to (or intended not to) have any tags. """
    name = files.remove_forbidden_chars(name, name_only)
    for c in FORBIDDEN_CHARS:
        name = name.replace(c, "")
    return name


TAG_RE = re.compile(r"(.*)(\[[^\[\]]+\])")


def name_parts(filename: str) -> tuple[str, str, str]:
    p = Path(filename)
    stem_and_tags = p.stem
    suffix = p.suffix
    match = TAG_RE.match(stem_and_tags)
    if match:
        stem, ts = match.groups()
    else:
        stem = stem_and_tags
        ts = ""
    # suffix can be None
    return (stem, ts, suffix)


def stem(filename: str) -> str:
    return name_parts(filename)[0]


def name(filename: str) -> str:
    name, _, suffix = name_parts(filename)
    return name + suffix

# tags handled by everything else, no function to return that piece of the filename


def suffix(filename: str) -> str:
    # tags don't change the suffix since they are part of the stem according to pathlib
    return Path(filename).suffix


def _remove_whitespace(tags: Iterable[str]) -> bset[str]:
    """ Removes leading and trailing whitespace and removes tags that are entirely whitespace. """
    return {t.strip() for t in tags if not re.match(r"^\s*$", t)}


def set(filename: str, tags: Iterable[str]) -> str:
    tags = sorted(_remove_whitespace(tags))
    name, _, suffix = name_parts(filename)
    if len(tags) == 0:
        return name + suffix
    return name + "[" + " ".join(tags) + "]" + suffix


def get(filename: str) -> bset[str]:
    _, ts, _ = name_parts(filename)
    if ts == "":
        return bset()
    else:
        # remove []
        ts = ts[1:-1]
        return bset(re.split(r"\s+", ts))


def add(filename: str, new_tags: Iterable[str]) -> str:
    return set(filename, get(filename) | bset(new_tags))


def remove(filename: str, remove_tags: Iterable[str]) -> str:
    return set(filename, get(filename) - bset(remove_tags))


def rename(filename: str, new_name: str) -> str:
    return new_name + filename[len(name(filename)):]


def _prune_walk_kwargs_set_ignore_hidden_true(kwargs):
    # default ignore_hidden to True for functions in this module using files.walk
    files.prune_walk_kwargs(kwargs)
    if "ignore_hidden" not in kwargs:
        kwargs["ignore_hidden"] = True


def matching_files(root: files.PathLike, name_suffix_re_pattern: str | None = None, tag_expression: str | BooleanExpression | None = None, recursive: bool = True, **kwargs) -> Iterable[Path]:
    r""" The name_suffix_re_pattern is a regular expression that is applied ONLY to the name and suffix of the file, with the tags removed. It may match any part of this. For example, a file with the full name "foo[bar baz].txt" will match pattern="oo\\.tx" """
    if isinstance(tag_expression, str):
        tag_expression: BooleanExpression = BooleanExpression.compile(
            tag_expression)

    def file_action(f: Path, d: int):
        name, _, suffix = name_parts(f.name)
        full_name = name+suffix
        matches_name_suffix = name_suffix_re_pattern is None or re.search(
            name_suffix_re_pattern, full_name)

        file_tags = get(f.name)
        matches_tag_expression = tag_expression is None or tag_expression.match(
            file_tags)
        if matches_name_suffix and matches_tag_expression:
            yield f

    _prune_walk_kwargs_set_ignore_hidden_true(kwargs)
    return files.walk(root, file_action=file_action, **kwargs)


def tag_in_folder(root: files.PathLike, tags: Iterable[str] = [], *, remove_tags=[], output=False, **matching_files_args) -> int:
    """ Adds/removes the tags to each file in the root folder if its name matches the regular expression pattern and/or set of match tags (the default None parameters match anything). Returns number of files moved. """
    tags = bset(tags)
    planned_moves = {}

    for f in matching_files(root, **matching_files_args):
        new_name = remove(add(f.name, tags), remove_tags)
        if f.name != new_name:
            planned_moves[f] = f.with_name(new_name)

    return files.move_by_dict(planned_moves, output=output)


def collect(root: files.PathLike, **kwargs) -> dict[str, int]:
    """ Returns all of the tags on files in this folder, along with counts. """
    collected_tags = {}

    def file_action(f: Path, d: int):
        for t in get(f.name):
            collected_tags[t] = collected_tags.get(t, 0) + 1

    _prune_walk_kwargs_set_ignore_hidden_true(kwargs)
    files.walk(root, file_action=file_action, side_effects=True, **kwargs)

    return collected_tags


def map_to_folders(root: files.PathLike, tags: Iterable[str], skip_dir: Callable[[Path, int], bool] | None = None, **kwargs) -> dict[str, bset[Path]]:
    """ Match each tag to a folder with the tag in its name (as a space-separated list).  """
    tags = bset(tags)
    tags_to_folders: dict[str, bset] = {}

    def dir_action(f: Path, d: int):
        tags_in_name = _remove_whitespace(f.name.split())
        for t in tags & tags_in_name:
            if not t in tags_to_folders:
                tags_to_folders[t] = bset()
            tags_to_folders[t].add(f)

    _prune_walk_kwargs_set_ignore_hidden_true(kwargs)
    files.walk(root, dir_action=dir_action,
               skip_dir=skip_dir, side_effects=True)

    return tags_to_folders


def tag_by_folder(root: files.PathLike):
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
    result = name_parts("file.txt")
    assert result == ("file", "", ".txt"), result
    result = name_parts("file[tag1].txt")
    assert result == ("file", "[tag1]", ".txt"), result
    result = name_parts("file[tag1 tag2].txt")
    assert result == ("file", "[tag1 tag2]", ".txt"), result
    result = name_parts("asdf")
    assert result == ("asdf", "", ""), result
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
