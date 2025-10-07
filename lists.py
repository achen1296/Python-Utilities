# (c) Andrew Chen (https://github.com/achen1296)

import math
from iterables import random_from  # used to be defined in this file, backward compatibility
import re
from io import StringIO
from typing import Any, Callable, Hashable, Iterable, Literal, Sequence

import files
from file_backed_data import FileBackedData


def read_file_lists(filename: files.PathLike, *, list_separator="\\s*\n\\s*", list_item_separator: str = "\\s*,\\s*", comment: str = "\\s*#", encoding="utf8", empty_on_not_exist: bool = False) -> Iterable[list[str]]:
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


def count[T:Hashable](lst: Iterable[T], bucket: Callable[[Any], T] = lambda x: x, initial_counts: dict[T, int] | None = None) -> dict[T, int]:
    counts = initial_counts or {}
    for i in lst:
        b = bucket(i)
        counts[b] = counts.get(b, 0) + 1
    return counts


def histogram[T:Hashable](counts: dict[T, int], file: files.PathLike | None = None, *, sort_by: Callable | Literal[False] | Literal["count"] = "count", bar_char="-", encoding="utf8", **open_kwargs) -> str:
    """ Pass in a dictionary as returned by count(). If file is specified, the result is written to that file. Whether or not it is specified, the result is also returned. sort_by can be a Callable key argument for sorted() on counts.keys(), `"count"`, or `False`, which causes the arbitrary order of iteration over the dict to be used. """
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

    def __init__(self, file: files.PathLike, value_transform: Callable[[str], T] = (lambda x: x), *args, **kwargs):
        self.value_transform = value_transform
        super().__init__(file=file, *args, **kwargs)

    def read(self, *args, **kwargs):
        if self.file.exists():
            self.extend(self.value_transform(v) for v in read_file_list(self.file, *args, **kwargs))

    def write(self, *args, **kwargs):
        write_file_list(self.file, self, *args,
                        **kwargs)


try:
    import numpy as np
except ModuleNotFoundError:
    pass
else:
    class TriangularArray[T]:
        """ Represents a square 2D array that is symmetrical, i.e. where swapping the indices points to the same information, without actually duplicating values. Can be `expand`ed but not contracted (copy the values to a new, smaller one instead if desired).

        Note that it behaves differently from an actual 2D array in that:
        - `len` will return the side length, not the number of elements
        - `iter` will return an iterator that produces `r`(ow index), `c`(olumn index), `v`(alue) tuples, not rows
        """

        @staticmethod
        def triangular_number(n: int):
            return n*(n+1)//2

        @staticmethod
        def _index(x: int, y: int):
            small = min(x, y)
            large = max(x, y)
            return TriangularArray.triangular_number(large)+small

        def __init__(self, side_length: int | None = None, *, data: list[T] | np.ndarray | None = None, numpy_array=False, default_value: T = 0.):
            """ Specify either side_length or data. data will take precedence if it is not None, and the correct side_length will be calculated accordingly. This will also override the numpy_array argument. data is expected to be in the same format/memory order this class creates, not an ordinary 2D array, so that the class can be easily copied/expanded/loaded from file. If the data length is not a triangular number, it is filled with default_value until it is. """
            self.default_value = default_value

            self.data: list[T] | np.ndarray
            self.side_length: int
            self.numpy_array: bool

            if data is not None:
                self.data = data
                self.numpy_array = isinstance(self.data, np.ndarray)
                l = len(data)
                # check if length is a triangular number
                # if l = n*(n+1)//2, n an integer, then n < sqrt(2*l) < n+1 -> floor(sqrt(2*l)) == n
                n = math.floor(math.sqrt(2*l))
                t = self.triangular_number(n)
                if l > t:
                    # can have both l < t(n) (e.g. l=2 -> t(n)=3) and l > t (e.g. l=4 -> also t(n)=3)
                    # but always have t(n-1) < l < t(n+1), so either t(n) or t(n+1) is the next largest triangular number
                    # therefore if is sufficient, while is not needed
                    n += 1
                    t = self.triangular_number(n)
                self._resize(l, self.triangular_number(n))
                self.side_length = n
            else:
                self.numpy_array = numpy_array
                if side_length is None:
                    raise TypeError("must specify side_length if data is not specified")
                self.side_length = side_length
                one_d_length = self.triangular_number(side_length)
                if numpy_array:
                    self.data = np.ndarray((one_d_length,))
                    self.data.fill(default_value)
                else:
                    self.data = [default_value] * one_d_length

        class Row:
            def __init__(self, tri_array: "TriangularArray[T]", x: int):
                self.tri_array = tri_array
                self.x = x

            def __getitem__(self, y: int) -> T:
                return self.tri_array.data[self.tri_array._index(self.x, y)]

            def __setitem__(self, y: int, v: T):
                self.tri_array.data[self.tri_array._index(self.x, y)] = v

            def __iter__(self) -> Iterable[T]:
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

        def __iter__(self) -> Iterable[tuple[int, int, T]]:
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

        def expand(self, n: int):
            old_length = self.triangular_number(self.side_length)
            self.side_length += n
            new_length = self.triangular_number(self.side_length)
            self._resize(old_length, new_length)

        def _resize(self, old_length: int, new_length: int):
            if self.numpy_array:
                assert isinstance(self.data, np.ndarray)
                self.data.resize(new_length, refcheck=False)
                self.data[old_length:].fill(self.default_value)
            else:
                assert isinstance(self.data, list)
                self.data += [self.default_value] * (new_length-old_length)
