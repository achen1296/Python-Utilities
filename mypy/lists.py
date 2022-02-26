import os
import re
import typing

from mypy import files


def read_file_lists(filename: os.PathLike, *, list_separator="\s*\n\s*", list_item_separator: str = "\s*,\s*", comment: str = "\s*#") -> typing.Generator:
    """Read a file as a list of lists. Use comment="" for no comments."""
    for list_str in files.re_split(filename, list_separator, encoding="utf-8"):
        if comment != "" and re.match(comment, list_str):
            continue
        yield re.split(list_item_separator, list_str)


def write_file_lists(filename: os.PathLike, lists: typing.Iterable[typing.Iterable], *, list_item_separator: str = ",", list_separator: str = "\n", text_mode="w", **open_kwargs) -> None:
    """Write a list of lists to a file."""
    with open(filename, text_mode, encoding="UTF-8", **open_kwargs) as f:
        for l in lists:
            first = True
            for i in l:
                if first:
                    first = False
                else:
                    f.write(list_item_separator)
                f.write(str(i))
            f.write(list_separator)


def read_file_list(filename: os.PathLike, *, separator: str = "\s*\n\s*") -> typing.Generator:
    return files.re_split(filename, separator)


def write_file_list(filename: os.PathLike, l: typing.Iterable, *, separator: str = "\n", text_mode="w", **open_kwargs):
    with open(filename, text_mode, encoding="UTF-8", **open_kwargs) as f:
        for i in l:
            f.write(i + separator)


def sort_file(filename: os.PathLike, **kwargs):
    l = read_file_list(filename, **kwargs)
    write_file_list(filename, sorted(l), **kwargs)


def remove_duplicates_in_place(l: list) -> list:
    """Still uses sets, but preserves the order of the remaining elements, which turning into a set and then back would not."""
    unique = set()
    i = 0
    while i < len(l):
        if l[i] in unique:
            del l[i]
        else:
            unique.add(l[i])
            i += 1
    return l
