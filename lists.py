import os
import random
import re
import typing

import files


def read_file_lists(filename: os.PathLike, *, list_separator="\s*\n\s*", list_item_separator: str = "\s*,\s*", comment: str = "\s*#", encoding="utf8") -> typing.Iterable[str]:
    """Read a file as a list of lists. Use comment="" for no comments."""
    for list_str in files.re_split(filename, list_separator, encoding=encoding):
        if comment != "" and re.match(comment, list_str):
            continue
        yield re.split(list_item_separator, list_str)


def write_file_lists(filename: os.PathLike, lists: typing.Iterable[typing.Iterable], *, list_item_separator: str = ",", list_separator: str = "\n", text_mode="w", encoding="utf8", **open_kwargs) -> None:
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


def read_file_list(filename: os.PathLike, *, separator: str = "\s*\n\s*", comment: str = "\s*#", **open_kwargs) -> typing.Iterable[str]:
    """Read a file as a list. Use comment="" for no comments."""
    for item in files.re_split(filename, separator, **open_kwargs):
        if comment != "" and re.match(comment, item):
            continue
        yield item


def write_file_list(filename: os.PathLike, l: typing.Iterable, *, separator: str = "\n", text_mode="w", encoding="utf8", **open_kwargs) -> None:
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


def cartesian_product(l1: typing.Iterable, *lists: typing.Iterable, first_fastest: bool = False) -> typing.Iterable[list]:
    if len(lists) == 0:
        for i in l1:
            yield [i]
    else:
        if first_fastest:
            for combo in cartesian_product(*lists, first_fastest=first_fastest):
                for i in l1:
                    yield [i] + combo
        else:
            for i in l1:
                for combo in cartesian_product(*lists, first_fastest=first_fastest):
                    yield [i] + combo


def combinations(l: typing.Iterable, n: int):
    """Generate all combinations of n unique elements from the list l exactly one time each. Out-of-bounds values for n are snapped in-bounds, i.e. if n < 0, then only a empty list is yieled, and if n > len(l) then l is yielded."""

    def combinations_recursive(l: list, n: int):
        if n <= 0:
            yield []
            return
        if n >= len(l):
            yield l
            return
        for i in range(0, len(l) - n + 1):
            for c in combinations_recursive(l[i+1:], n-1):
                yield l[i:i+1] + c

    return combinations_recursive(list(l), n)


def random_from(lst: typing.Iterable) -> typing.Any:
    while True:
        try:
            return lst[random.randrange(0, len(lst))]
        except TypeError:
            lst = list(lst)
        except ValueError:
            # empty iterable
            return None


def count(lst: typing.Iterable[typing.Hashable], bucket: typing.Callable[[typing.Any], typing.Hashable] = lambda x: x) -> dict[typing.Hashable, int]:
    counts = {}
    for i in lst:
        b = bucket(i)
        counts[b] = counts.get(b, 0) + 1
    return counts


def histogram(counts: dict, file: os.PathLike = None, *, sort_by="count", bar_char="-", encoding="utf8", **open_kwargs) -> str:
    """ Pass in a dictionary as returned by count(). If file is specified, the result is written to that file. Whether or not it is specified, the result is also returned. sort_by can be a Callable argument for sorted(), "count", or False, which causes the order of iteration over the dict to be used. """
    if sort_by is False:
        sorted_keys = counts.keys()
    elif sort_by == "count":
        sorted_keys = sorted(
            counts.keys(), key=lambda k: counts[k], reverse=True)
    else:
        sorted_keys = sorted(counts.keys())

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
