from typing import Hashable


class SetGroup:
    def __init__(self):
        self.internal_dict = {}

    def join(self, obj1: Hashable, obj2: Hashable) -> None:
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

    def __getitem__(self, obj: Hashable) -> set:
        return self.internal_dict[obj]

    def __contains__(self, obj: Hashable) -> bool:
        return obj in self.internal_dict

    def get_all(self) -> list[set]:
        found = set()
        sets = []
        for key in self.internal_dict:
            if key in found:
                continue
            found |= self.internal_dict[key]
            sets.append(self.internal_dict[key])
        return sets

    def __new_set(self, obj1: Hashable, obj2: Hashable) -> None:
        self.internal_dict[obj1] = {obj1, obj2}
        self.internal_dict[obj2] = self.internal_dict[obj1]

    def __add_to_set(self, target: Hashable, new: Hashable) -> None:
        self.internal_dict[target].add(new)
        self.internal_dict[new] = self.internal_dict[target]

    def __join_sets(self, obj1: Hashable, obj2: Hashable) -> None:
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
