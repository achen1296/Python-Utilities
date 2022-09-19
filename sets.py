from typing import Hashable, Iterable


class Partition:
    """For constructing representations of partitions/equivalence relations. If you have a Partition p, p[key] returns the cell containing the key. Objects can also be removed this way using the del keyword."""

    def __init__(self, initial_sets=None):
        self._internal_dict: dict[Hashable, set] = {}
        if initial_sets is not None:
            self.merge(initial_sets)

    def merge(self, other_partition: Iterable[Iterable[Hashable]]):
        """ The resulting changes from this method may not match the argument if it is not really a Partition. Of course, the state of this Partition also influences the result. """
        for s in other_partition:
            self.join(*s)

    def join(self, obj1: Hashable, /, *objs: Hashable):
        """ Joins the cells containing each object. Objects not already in any cell are simply added. """
        self.__join_two(obj1, obj1)
        for o in objs:
            self.__join_two(obj1, o)

    def __join_two(self, obj1: Hashable, obj2: Hashable):
        if obj1 in self._internal_dict:
            if obj2 in self._internal_dict:
                self.__join_sets(obj1, obj2)
            else:
                self.__add_to_set(obj1, obj2)
        else:
            if obj2 in self._internal_dict:
                self.__add_to_set(obj2, obj1)
            else:
                self.__new_set(obj1, obj2)

    def joined(self, obj1: Hashable, /, *objs: Hashable):
        """ Checks if the objects are all in the same cell. Specifying only one argument just checks for membership. """
        if not obj1 in self:
            return False
        for o in objs:
            if not o in self._internal_dict[obj1]:
                return False
        return True

    def __eq__(self, other_partition: Iterable[Iterable[Hashable]]) -> bool:
        for s in other_partition:
            first = None
            for item in s:
                if first is None:
                    first = item
                elif not self.joined(first, item):
                    return False
        return True

    def __len__(self):
        return len(self._internal_dict)

    def __getitem__(self, obj: Hashable) -> set:
        return self._internal_dict[obj]

    def __delitem__(self, obj: Hashable):
        self._internal_dict[obj].remove(obj)
        del self._internal_dict[obj]

    def __contains__(self, obj: Hashable) -> bool:
        return obj in self._internal_dict

    def __iter__(self):
        found = set()
        for key in self._internal_dict:
            if key in found:
                continue
            found |= self._internal_dict[key]
            yield self._internal_dict[key]

    def __new_set(self, obj1: Hashable, obj2: Hashable) -> None:
        new_set = {obj1, obj2}
        self._internal_dict[obj1] = new_set
        self._internal_dict[obj2] = new_set

    def __add_to_set(self, target: Hashable, new: Hashable) -> None:
        target_set = self._internal_dict[target]
        target_set.add(new)
        self._internal_dict[new] = target_set

    def __join_sets(self, obj1: Hashable, obj2: Hashable) -> None:
        if self.joined(obj1, obj2):
            return

        set1 = self._internal_dict[obj1]
        set2 = self._internal_dict[obj2]

        if len(set1) < len(set2):
            small_set = set1
            large_set = set2
        else:
            small_set = set2
            large_set = set1

        large_set |= small_set
        for o in small_set:
            self._internal_dict[o] = large_set

    def __repr__(self):
        return "Partition([" + ",".join([str(s) for s in self]) + "])"
