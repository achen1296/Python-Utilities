import os
import random
import re
from typing import Any, Callable, Hashable, Iterable

import files


def read_file_lists(filename: os.PathLike, *, list_separator="\s*\n\s*", list_item_separator: str = "\s*,\s*", comment: str = "\s*#", encoding="utf8", empty_on_not_exist: bool = False) -> Iterable[str]:
    """Read a file as a list (technically a generator) of lists. Use comment=None for no comments."""
    for list_str in files.re_split(filename, list_separator, encoding=encoding, empty_on_not_exist=empty_on_not_exist):
        if comment and re.match(comment, list_str):
            continue
        yield re.split(list_item_separator, list_str)


def write_file_lists(filename: os.PathLike, lists: Iterable[Iterable], *, list_item_separator: str = ",", list_separator: str = "\n", text_mode="w", encoding="utf8", **open_kwargs) -> None:
    """Write a list of lists to a file."""
    with open(filename, text_mode, encoding=encoding, **open_kwargs) as f:
        for l in lists:
            first = True
            for i in l:
                if first:
                    first = False
                else:
                    f.write(list_item_separator)
                f.write(str(i))
            f.write(list_separator)


def read_file_list(filename: os.PathLike, *, separator: str = "\s*\n\s*", comment: str = "\s*#", **re_split_kwargs) -> Iterable[str]:
    """Read a file as a list (technically a generator). Use comment=None for no comments."""
    for item in files.re_split(filename, separator, **re_split_kwargs):
        if comment and re.match(comment, item):
            continue
        yield item


def write_file_list(filename: os.PathLike, l: Iterable, *, separator: str = "\n", text_mode="w", encoding="utf8", **open_kwargs) -> None:
    with open(filename, text_mode, encoding=encoding, **open_kwargs) as f:
        first = True
        for i in l:
            if first:
                first = False
            else:
                f.write(separator)
            f.write(str(i))


def sort_file(filename: os.PathLike, remove_duplicates: bool = False, sort_key=None, **open_kwargs) -> None:
    l = read_file_list(filename, **open_kwargs)
    if remove_duplicates:
        l = set(l)
    l = sorted(l, key=sort_key)
    write_file_list(filename, l, **open_kwargs)


def remove_duplicates_file(filename: os.PathLike, **open_kwargs) -> None:
    sort_file(filename, remove_duplicates=True, **open_kwargs)


def remove_duplicates_in_place(l: list) -> list:
    """Still uses sets, but preserves the order of the remaining elements, which turning into a set and then back may not. Returns the input list."""
    unique = set()
    i = 0
    while i < len(l):
        if l[i] in unique:
            del l[i]
        else:
            unique.add(l[i])
            i += 1
    return l


def random_from(lst: Iterable) -> Any:
    if len(lst) == 0:
        return None
    if not isinstance(lst, list):
        lst = list(lst)
    return lst[random.randrange(0, len(lst))]


def count(lst: Iterable[Hashable], bucket: Callable[[Any], Hashable] = lambda x: x) -> dict[Hashable, int]:
    counts = {}
    for i in lst:
        b = bucket(i)
        counts[b] = counts.get(b, 0) + 1
    return counts


def histogram(counts: dict, file: os.PathLike = None, *, sort_by="count", bar_char="-", encoding="utf8", **open_kwargs) -> str:
    """ Pass in a dictionary as returned by count(). If file is specified, the result is written to that file. Whether or not it is specified, the result is also returned. sort_by can be a Callable key argument for sorted() on counts.keys(), "count", or False, which causes the order of iteration over the dict to be used. """
    if sort_by is False:
        sorted_keys = counts.keys()
    elif sort_by == "count":
        sorted_keys = sorted(
            counts.keys(), key=lambda k: counts[k], reverse=True)
    else:
        sorted_keys = sorted(counts.keys(), key=sort_by)

    longest_key = max((len(str(k)) for k in counts))
    longest_count = max((len(str(k)) for k in counts.values()))

    hist_str = ""
    for k in sorted_keys:
        # keys padded to length of longest key and right-aligned
        c = counts[k]
        hist_str += format(str(k), ">" + str(longest_key)) + \
            " " + format(str(c), ">" + str(longest_count)) + \
            " " + (bar_char * c) + "\n"

    if file is not None:
        with open(file, "w", encoding=encoding, **open_kwargs) as f:
            f.write(hist_str)

    return hist_str
