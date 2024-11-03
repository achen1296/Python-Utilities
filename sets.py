from typing import Callable, Hashable, Iterable

import files
import lists
from file_backed_data import FileBackedData


def nonempty_intersection(s1: set, s2: set) -> bool:
    len1 = len(s1)
    len2 = len(s2)
    if len1 <= len2:
        small = s1
        large = s2
    else:
        small = s2
        large = s1
    for e in small:
        if e in large:
            return True
    return False


class DisjointSetException(Exception):
    pass


class DisjointSets:

    def __init__(self):
        # maps a subset element to its parent
        self._parent: dict[Hashable, Hashable] = {}
        # maps a subset representative to the subset size
        self._subset_size: dict[Hashable, int] = {}

    def new_subset(self, e1: Hashable, *es: Hashable):
        """ Create a new subset. """
        if e1 in self._parent:
            raise DisjointSetException(f"{e1} already in a subset")
        for e in es:
            if e in self._parent:
                raise DisjointSetException(f"{e} already in a subset")
        self._parent[e1] = e1
        for e in es:
            self._parent[e] = e1
        self._subset_size[e1] = 1 + len(es)

    def representative(self, e: Hashable) -> Hashable:
        """ Find the representative element for e. Performs path compression. """
        if e not in self._parent:
            # placing this check here suffices for all other methods because they all query representatives
            raise DisjointSetException(f"{e} not in a subset")

        p = self._parent[e]
        if e == p:
            return e

        r = self.representative(p)
        self._parent[e] = r
        return r

    def same_subset(self, e1: Hashable, e2: Hashable, *es: Hashable):
        r = self.representative(e1)
        return r == self.representative(e2) and all(r == self.representative(e) for e in es)

    def subset_size(self, e: Hashable):
        return self._subset_size[self.representative(e)]

    def union(self, e1: Hashable, e2: Hashable, *es: Hashable):
        """ Combine the subsets containing the elements. Uses weighted union. """
        self._union_two(e1, e2)
        for e in es:
            self._union_two(e1, e)

    def _union_two(self, e1: Hashable, e2: Hashable):
        """ Combine the subsets containing e1 and e2 (does nothing if already in the same one). Uses weighted union (if the subsets are the same size, e1's representative is the new overall representative). """
        r1 = self.representative(e1)
        r2 = self.representative(e2)
        if r1 == r2:
            return

        s1 = self._subset_size[r1]
        s2 = self._subset_size[r2]
        if s1 < s2:
            self._parent[r1] = r2
            self._subset_size[r2] = s1+s2
            del self._subset_size[r1]
        else:
            self._parent[r2] = r1
            self._subset_size[r1] = s1+s2
            del self._subset_size[r2]

    def __len__(self):
        return len(self._parent)

    def __contains__(self, e: Hashable):
        return e in self._parent

    def __getitem__(self, e: Hashable):
        """ Expensive operation! Get the subset containing e. """
        r = self.representative(e)
        subset = set()
        for e2 in self._parent:
            if self.representative(e2) == r:
                subset.add(e2)
        return subset

    def __delitem__(self, e: Hashable):
        """ Expensive operation! Remove e. """
        # need to scan over all elements anyway to find those with e as parent
        subset = self[e]
        subset.remove(e)
        r = self.representative(e)
        del self._parent[e]
        del self._subset_size[r]

        r = None
        for e in subset:
            if not r:
                r = e
            self._parent[e] = r
        self._subset_size[r] = len(subset)

    def __iter__(self):
        return iter(self._parent)

    def subsets(self) -> Iterable[set]:
        """ Expensive operation! Return iterable of all subsets. """
        subsets: dict[Hashable, set] = {}
        for e in self._parent:
            r = self.representative(e)
            if r not in subsets:
                subsets[r] = set()
            subsets[r].add(e)
        return subsets.values()

    def __eq__(self, other: object):
        """ Expensive operation! Compares subset contents only, not tree structure. """

        if not isinstance(other, DisjointSets):
            return False

        for e in self:
            if not e in other:
                return False

        for e in other:
            if not e in self:
                return False

        corresponding_rep = {}
        for e in self:
            self_r = self.representative(e)
            other_r = other.representative(e)

            if self_r not in corresponding_rep:
                corresponding_rep[self_r] = other_r
            else:
                if other_r != corresponding_rep:
                    return False

        return True


class FileBackedSet[T](FileBackedData, set[T]):
    """ Keep in mind that all data will be converted to strings when writing to file! """

    def __init__(self, file: files.PathLike, sort_keys: Callable | None = None, value_transform: Callable[[str], T] = (lambda x: x), *args, **kwargs):
        super().__init__(file=file, *args, **kwargs)
        self.sort_keys = sort_keys
        self.value_transform = value_transform

    def read(self, *args, **kwargs):
        if self.file.exists():
            for v in lists.read_file_list(self.file, *args, **kwargs):
                self.add(self.value_transform(v))

    def write(self, *args, **kwargs):
        lists.write_file_list(self.file, sorted(
            self, key=self.sort_keys), *args, **kwargs)
