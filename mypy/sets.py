from typing import Hashable


class SetGroup:
    """Represents a group of sets whose elements and provides the join operation. This is intended for constructing representations of elements that are related to each other if they are both related to another element. self[key] returns the set containing the key. Objects can also be deleted."""

    def __init__(self):
        self.internal_dict = {}

    def join(self, obj1: Hashable, obj2: Hashable) -> None:
        """Sets in the group can be joined together by calling join on one element from each. If an object is joined into a set but is not already part of another set in the group, it is simply added to that set. If both objects that are joined together are not in an existing set, they form a new set together. """
        if obj1 in self.internal_dict:
            if obj2 in self.internal_dict:
                self.__join_sets(obj1, obj2)
            else:
                self.__add_to_set(obj1, obj2)
        else:
            if obj2 in self.internal_dict:
                self.__add_to_set(obj2, obj1)
            else:
                self.__new_set(obj1, obj2)

    def joined(self, obj1: Hashable, obj2: Hashable) -> bool:
        return obj1 in self.internal_dict and obj2 in self.internal_dict and obj2 in self.internal_dict[obj1]

    def __len__(self):
        return len(self.internal_dict)

    def __getitem__(self, obj: Hashable) -> set:
        return self.internal_dict[obj]

    def __delitem__(self, obj: Hashable):
        self.internal_dict[obj].remove(obj)
        del self.internal_dict[obj]

    def __contains__(self, obj: Hashable) -> bool:
        return obj in self.internal_dict

    def __iter__(self):
        found = set()
        for key in self.internal_dict:
            if key in found:
                continue
            found |= self.internal_dict[key]
            yield self.internal_dict[key]

    def __new_set(self, obj1: Hashable, obj2: Hashable) -> None:
        self.internal_dict[obj1] = {obj1, obj2}
        self.internal_dict[obj2] = self.internal_dict[obj1]

    def __add_to_set(self, target: Hashable, new: Hashable) -> None:
        self.internal_dict[target].add(new)
        self.internal_dict[new] = self.internal_dict[target]

    def __join_sets(self, obj1: Hashable, obj2: Hashable) -> None:
        if self.joined(obj1, obj2):
            return

        set1 = self.internal_dict[obj1]
        set2 = self.internal_dict[obj2]

        if len(set1) < len(set2):
            small_set = set1
            large_set = set2
        else:
            small_set = set2
            large_set = set1

        large_set |= small_set
        for o in small_set:
            self.internal_dict[o] = large_set
