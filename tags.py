import os
import re
from builtins import set as bset
from pathlib import Path
from typing import Callable, Iterable

import files

NAME_TAGS_SUFFIX_RE = re.compile("^(.*)(\[.*?\])(\.\w+)?$")
NAME_SUFFIX_RE = re.compile("^(.*?)(\.\w+)?$")


def remove_forbidden_chars(name: str, name_only=False):
    """ Variant of files.remove_forbidden_chars that also removes square brackets, intended to be used on files that are known not to have any tags. """
    name = files.remove_forbidden_chars(name, name_only)
    chars = "[]()|!"
    for c in chars:
        name = name.replace(c, "")
    return name


def name_and_suffix(filename: str) -> tuple[str, str]:
    match = NAME_TAGS_SUFFIX_RE.match(filename)
    if match:
        name = match.group(1)
        suffix = match.group(3)
    else:
        match = NAME_SUFFIX_RE.match(filename)
        name = match.group(1)
        suffix = match.group(2)
    # ext can be None
    return (name, suffix if suffix else "")


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


def _remove_whitespace(tags: Iterable[str]) -> bset[str]:
    """ Removes leading and trailing whitespace and removes tags that are entirely whitespace. """
    return {t.strip() for t in tags if not re.match("^\s*$", t)}


def set(filename: str, tags: Iterable[str]) -> str:
    tags = sorted(_remove_whitespace(tags))
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


class TagExpressionException(Exception):
    pass


class TagExpression:
    def match(self, tags: Iterable[str]):
        return False

    @staticmethod
    def compile(tag_expression_str: str):
        s = "("+tag_expression_str+")"

        def _compile_and_or(i: int, expect_paren=False) -> tuple[TagExpression, int]:
            # represents an overall and, each sublist is an or
            and_or_sub_expressions = [[]]
            while True:
                # consume whitespace
                i += len(re.match("\s*", s[i:]).group(0))
                if expect_paren:
                    if i >= len(s):
                        raise TagExpressionException(
                            "Not enough closing parentheses for tag expression " + tag_expression_str)
                    elif s[i] == ")":
                        break
                if i >= len(s):
                    break
                if s[i] == "&":
                    and_or_sub_expressions.append([])
                    i += 1
                    continue
                sub, i = _compile(i)
                and_or_sub_expressions[-1].append(sub)
            and_or_sub_expressions = [subs[0]
                                      if len(subs) == 1 else
                                      TagExpressionOr(*subs)
                                      for subs in and_or_sub_expressions]
            if len(and_or_sub_expressions) == 1:
                return and_or_sub_expressions[0], i+1
            return TagExpressionAnd(*and_or_sub_expressions), i+1

        def _compile(i: int) -> tuple[TagExpression, int]:
            c = s[i]
            if c == "!":
                sub, i = _compile(i+1)
                return TagExpressionNot(sub), i
            if s[i] == "(":
                return _compile_and_or(i+1, expect_paren=True)
            match = re.match("\w+", s[i:])
            if not match:
                raise TagExpressionException("Unsupported character " + s[i])
            tag = match.group(0)
            return TagExpressionSingle(tag), i + len(tag)

        exp, _ = _compile_and_or(0)
        return exp


class TagExpressionSingle(TagExpression):
    def __init__(self, tag: str):
        self.tag = tag

    def match(self, tags: Iterable[str]):
        return self.tag in tags

    def __repr__(self):
        return "TagExpressionSingle(\""+self.tag+"\")"

    def __eq__(self, other):
        return isinstance(other, TagExpressionSingle) and self.tag == other.tag


class TagExpressionAnd(TagExpression):
    def __init__(self, *sub_expressions: TagExpression):
        self.sub_expressions = sub_expressions

    def match(self, tags: Iterable[str]):
        return all(sub.match(tags) for sub in self.sub_expressions)

    def __repr__(self):
        return "TagExpressionAnd("+", ".join((repr(sub) for sub in self.sub_expressions))+")"

    def __eq__(self, other):
        # not order independent
        try:
            return isinstance(other, TagExpressionAnd) and all(sub_self == sub_other for sub_self, sub_other in zip(self.sub_expressions, other.sub_expressions, strict=True))
        except ValueError:
            # from zip
            return False


class TagExpressionOr(TagExpression):
    def __init__(self, *sub_expressions: TagExpression):
        self.sub_expressions = sub_expressions

    def match(self, tags: Iterable[str]):
        return any(sub.match(tags) for sub in self.sub_expressions)

    def __repr__(self):
        return "TagExpressionOr("+", ".join((repr(sub) for sub in self.sub_expressions))+")"

    def __eq__(self, other):
        # not order independent
        try:
            return isinstance(other, TagExpressionOr) and all(sub_self == sub_other for sub_self, sub_other in zip(self.sub_expressions, other.sub_expressions, strict=True))
        except ValueError:
            # from zip
            return False


class TagExpressionNot(TagExpression):
    def __init__(self, sub_expression: TagExpression):
        self.sub_expression = sub_expression

    def match(self, tags: Iterable[str]):
        return not self.sub_expression.match(tags)

    def __repr__(self):
        return "TagExpressionNot("+repr(self.sub_expression)+")"

    def __eq__(self, other):
        # not order independent
        return isinstance(other, TagExpressionNot) and self.sub_expression == other.sub_expression


def matching_files(root: os.PathLike, name_suffix_re_pattern: str = None, tag_expression: str = None, recursive: bool = True) -> Iterable[Path]:
    r""" The name_suffix_re_pattern is a regular expression that is applied ONLY to the name and suffix of the file, with the tags removed. It may match any part of this. For example, a file with the full name "foo[bar baz].txt" will match pattern="oo\\.tx" """
    if tag_expression is not None:
        tag_expression: TagExpression = TagExpression.compile(tag_expression)

    def file_action(f: Path, d: int):
        name, suffix = name_and_suffix(f.name)
        full_name = name+suffix
        matches_name_suffix = name_suffix_re_pattern is None or re.search(
            name_suffix_re_pattern, full_name)

        file_tags = get(f.name)
        matches_tag_expression = tag_expression is None or tag_expression.match(
            file_tags)
        if matches_name_suffix and matches_tag_expression:
            yield f

    def skip_dir(f: Path, d: int):
        # still go over the top-level folder's contents if not recursive
        return (not recursive) and d > 0

    return files.walk(root, file_action=file_action, skip_dir=skip_dir)


def tag_in_folder(root: os.PathLike, tags: Iterable[str] = [], *, remove_tags=[], **matching_files_args) -> None:
    """ Adds/removes the tags to each file in the root folder if its name matches the regular expression pattern and/or set of match tags (the default None parameters match anything). """
    tags = bset(tags)
    planned_moves = {}

    for f in matching_files(root, **matching_files_args):
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

    files.walk(root, file_action=file_action, side_effects=True)

    return collected_tags


def map_to_folders(root: os.PathLike, tags: Iterable[str], skip_dir: Callable[[Path, int], bool] = None) -> dict[str, bset[Path]]:
    """ Match each tag to a folder with the tag in its name (as a space-separated list).  """
    tags = bset(tags)
    tags_to_folders: dict[str, bset] = {}

    def dir_action(f: Path, d: int):
        tags_in_name = _remove_whitespace(f.name.split())
        for t in tags & tags_in_name:
            if not t in tags_to_folders:
                tags_to_folders[t] = bset()
            tags_to_folders[t].add(f)

    files.walk(root, dir_action=dir_action,
               skip_dir=skip_dir, side_effects=True)

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

    result = TagExpression.compile("asdf")
    assert result == TagExpressionSingle("asdf"), result
    result = TagExpression.compile("a b c d e")
    assert result == TagExpressionOr(TagExpressionSingle(
        "a"), TagExpressionSingle("b"), TagExpressionSingle("c"), TagExpressionSingle("d"), TagExpressionSingle("e")), result
    result = TagExpression.compile("a b c&d e")
    assert result == TagExpressionAnd(
        TagExpressionOr(TagExpressionSingle(
            "a"), TagExpressionSingle("b"), TagExpressionSingle("c")),
        TagExpressionOr(TagExpressionSingle("d"), TagExpressionSingle("e"))
    ), result
    result = TagExpression.compile("a !b (!c&d) e")
    assert result == TagExpressionOr(
        TagExpressionSingle("a"),
        TagExpressionNot(TagExpressionSingle("b")),
        TagExpressionAnd(
            TagExpressionNot(TagExpressionSingle("c")),
            TagExpressionSingle("d")
        ),
        TagExpressionSingle("e")
    ), result
    result = TagExpression.compile("a (!b !(!c&d) e)")
    assert result == TagExpressionOr(
        TagExpressionSingle("a"),
        TagExpressionOr(
            TagExpressionNot(TagExpressionSingle("b")),
            TagExpressionNot(
                TagExpressionAnd(
                    TagExpressionNot(TagExpressionSingle("c")),
                    TagExpressionSingle("d")
                )
            ),
            TagExpressionSingle("e")
        )
    ), result
    assert result.match(["a"])
    assert result.match(["e"])
    assert not result.match(["b", "d"])
