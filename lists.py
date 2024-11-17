import random
import re
from io import StringIO
from pathlib import Path
from typing import (Any, Callable, Hashable, Iterable, Self, Sequence, Sized,
                    SupportsIndex)

import numpy as np

import files
from file_backed_data import FileBackedData


def read_file_lists(filename: files.PathLike, *, list_separator="\\s*\n\\s*", list_item_separator: str = "\\s*,\\s*", comment: str = "\\s*#", encoding="utf8", empty_on_not_exist: bool = False) -> Iterable[str]:
    """Read a file as a list (technically a generator) of lists. Use comment=None for no comments."""
    for list_str in files.re_split(filename, list_separator, encoding=encoding, empty_on_not_exist=empty_on_not_exist):
        if comment and re.match(comment, list_str):
            continue
        yield re.split(list_item_separator, list_str)


def write_file_lists(filename: files.PathLike, lists: Iterable[Iterable], *, list_item_separator: str = ",", list_separator: str = "\n", text_mode="w", encoding="utf8", **open_kwargs) -> None:
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


def read_file_list(filename: files.PathLike, *, separator: str = "\\s*\n\\s*", comment: str = "\\s*#", **re_split_kwargs) -> Iterable[str]:
    """Read a file as a list (technically a generator). Use comment=None for no comments."""
    for item in files.re_split(filename, separator, **re_split_kwargs):
        if comment and re.match(comment, item):
            continue
        yield item


def write_file_list(filename: files.PathLike, l: Iterable, *, separator: str = "\n", text_mode="w", encoding="utf8", **open_kwargs) -> None:
    with open(filename, text_mode, encoding=encoding, **open_kwargs) as f:
        first = True
        for i in l:
            if first:
                first = False
            else:
                f.write(separator)
            f.write(str(i))


def sort_file(filename: files.PathLike, remove_duplicates: bool = False, sort_key=None, **open_kwargs) -> None:
    l = read_file_list(filename, **open_kwargs)
    if remove_duplicates:
        l = set(l)
    l = sorted(l, key=sort_key)
    write_file_list(filename, l, **open_kwargs)


def remove_duplicates_file(filename: files.PathLike, **open_kwargs) -> None:
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
    if not isinstance(lst, list):
        lst = list(lst)
    if len(lst) == 0:
        return None
    return lst[random.randrange(0, len(lst))]


def count(lst: Iterable[Hashable], bucket: Callable[[Any], Hashable] = lambda x: x, initial_counts: dict[Hashable, int] | None = None) -> dict[Hashable, int]:
    counts = initial_counts or {}
    for i in lst:
        b = bucket(i)
        counts[b] = counts.get(b, 0) + 1
    return counts


def histogram(counts: dict, file: files.PathLike = None, *, sort_by="count", bar_char="-", encoding="utf8", **open_kwargs) -> str:
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


class FileBackedList[T](FileBackedData, list):
    """ Keep in mind that all data will be converted to strings when writing to file! """

    def read(self, value_transform: Callable[[str], T] = (lambda x: x), *args, **kwargs):
        self.value_transform = value_transform
        if self.file.exists():
            self.extend(self.value_transform(v) for v in read_file_list(self.file, *args, **kwargs))

    def write(self, *args, **kwargs):
        write_file_list(self.file, self, *args,
                        **kwargs)


class TriangularArray[T]:
    """ Represents a square 2D array that is symmetrical, i.e. where swapping the indices points to the same information, without actually duplicating values.

    Note that it behaves differently from an actual 2D array in that:
    - len() will return the side length, not the number of elements
    - iter() will return an iterator that produces r(ow index), c(olumn index), v(alue) tuples, not rows
    """

    @staticmethod
    def triangular_number(n: int):
        return n*(n+1)//2

    @staticmethod
    def _index(x: int, y: int):
        small = min(x, y)
        large = max(x, y)
        return TriangularArray.triangular_number(large)+small

    def __init__(self, side_length: int, *, numpy_array=False, default_value: T = 0.):
        one_d_length = self.triangular_number(side_length)
        self.side_length = side_length
        self.default_value = default_value
        if numpy_array:
            self.data = np.ndarray((one_d_length,))
            self.data.fill(default_value)
        else:
            self.data = [default_value] * one_d_length

    class Row:
        def __init__(self, tri_array: "TriangularArray[T]", x: int):
            self.tri_array = tri_array
            self.x = x

        def __getitem__(self, y: int):
            return self.tri_array.data[self.tri_array._index(self.x, y)]

        def __setitem__(self, y: int, v: T):
            self.tri_array.data[self.tri_array._index(self.x, y)] = v

        def __iter__(self):
            for c in range(0, self.tri_array.side_length):
                yield self.tri_array.data[self.tri_array._index(self.x, c)]

        def __len__(self):
            return len(self.tri_array)

    def __getitem__(self, x: int):
        return self.Row(self, x)

    def __setitem__(self, x: int, values: Sequence[T]):
        if len(values) != self.side_length:
            raise TypeError("values must be same length as a single row")
        for y in range(0, self.side_length):
            self.data[self._index(x, y)] = values[y]

    def __iter__(self):
        i = 0
        for x in range(0, self.side_length):
            for y in range(0, x+1):
                # assert self._index(x, y) == i
                yield x, y, self.data[i]
                i += 1

    def __len__(self):
        return self.side_length

    def __str__(self):
        s = StringIO()
        s.write("[\n")
        i = 0
        for x in range(0, self.side_length):
            s.write("\t[")
            for y in range(0, x+1):
                # assert self._index(x, y) == i
                s.write(f"{self.data[i]}, ")
                i += 1
            s.write("]\n")
        s.write("]")
        return s.getvalue()

    def __repr__(self):
        return self.__str__()
