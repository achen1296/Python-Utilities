import os
import random
import re
import typing

import files


def read_file_lists(filename: os.PathLike, *, list_separator="\s*\n\s*", list_item_separator: str = "\s*,\s*", comment: str = "\s*#") -> typing.Iterable[str]:
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


def read_file_list(filename: os.PathLike, *, separator: str = "\s*\n\s*", comment: str = "\s*#", **kwargs) -> typing.Iterable[str]:
    """Read a file as a list. Use comment="" for no comments."""
    for item in files.re_split(filename, separator, **kwargs):
        if comment != "" and re.match(comment, item):
            continue
        yield item


def write_file_list(filename: os.PathLike, l: typing.Iterable, *, separator: str = "\n", text_mode="w", **open_kwargs):
    with open(filename, text_mode, encoding="UTF-8", **open_kwargs) as f:
        for i in l:
            f.write(str(i) + separator)


def sort_file(filename: os.PathLike, remove_duplicates: bool = False, **kwargs):
    l = read_file_list(filename, **kwargs)
    if remove_duplicates:
        l = set(l)
    l = sorted(l)
    write_file_list(filename, l, **kwargs)


def remove_duplicates_file(filename: os.PathLike, **kwargs):
    l = read_file_list(filename, **kwargs)
    write_file_list(filename, sorted(set(l)), **kwargs)


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


def combinations(items: list[list[int]]) -> typing.Iterable[list[int]]:
    # start with all indices at 0 -- in loop below, increment happens first, so start first index at -1
    indices = [0 for _ in range(0, len(items))]
    indices[-1] = -1

    stop = False
    while True:
        # increment indices to try next key
        i = len(indices) - 1
        while True:
            indices[i] += 1
            if indices[i] >= len(items[i]):
                indices[i] = 0
                i -= 1
                if i == -1:
                    # tried all keys
                    stop = True
                    break
            else:
                break
        if stop:
            break
        yield [items[i][j] for i, j in enumerate(indices)]


def random_from(lst: typing.Iterable):
    while True:
        try:
            return lst[random.randrange(0, len(lst))]
        except TypeError:
            lst = list(lst)
        except ValueError:
            # empty iterable
            return None
