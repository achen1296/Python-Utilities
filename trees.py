# (c) Andrew Chen (https://github.com/achen1296)

import math
import random

import lists


class KDDatum():
    def __init__(self,
                 coords: tuple[float, ...],
                 values: list):
        self.coords = coords
        self.values: list = values

    def __eq__(self, other):
        if not isinstance(other, KDDatum):
            return False
        # not order independent
        return self.coords == other.coords and self.values == other.values

    def __repr__(self):
        return f"KDDatum({self.coords!r}, {self.values!r})"


class KDNodeLeaf():
    def __init__(self,
                 data: list[KDDatum]):
        self.data = data
        self.update_bounding_box()

    def update_bounding_box(self):
        """ Assumes all data points have the same length (same number of dimensions) and that self.data is non-empty """
        self.bounding_box_min: list[float] = [
            math.inf] * len(self.data[0].coords)
        self.bounding_box_max: list[float] = [
            -math.inf] * len(self.data[0].coords)
        for d in self.data:
            pt = d.coords
            for i in range(0, len(pt)):
                self.bounding_box_min[i] = min(self.bounding_box_min[i], pt[i])
                self.bounding_box_max[i] = max(self.bounding_box_max[i], pt[i])

    def __repr__(self):
        return f"KDNodeLeaf({self.data!r})"

    def __eq__(self, other):
        if not isinstance(other, KDNodeLeaf):
            return False
        # not order independent
        return all(self_d == other_d for self_d, other_d in zip(self.data, other.data))


class KDNodeInternal():
    def __init__(self,
                 split_index: int,
                 split_value: float,
                 left: "KDNodeInternal | KDNodeLeaf",
                 right: "KDNodeInternal | KDNodeLeaf"):
        self.split_index = split_index
        self.split_value = split_value
        self.left = left
        self.right = right
        self.update_bounding_box()

    def update_bounding_box(self):
        """ Assumes there are two children, does not call update_bounding_box on them. """
        self.bounding_box_min: list[float] = [min(l, r) for l, r in zip(
            self.left.bounding_box_min, self.right.bounding_box_min)]
        self.bounding_box_max: list[float] = [max(l, r) for l, r in zip(
            self.left.bounding_box_max, self.right.bounding_box_max)]

    def __repr__(self):
        return f"KDNodeInternal({self.split_index!r}, {self.split_value!r}, {self.left!r}, {self.right!r})"

    def __eq__(self, other):
        if not isinstance(other, KDNodeInternal):
            return False
        # not structure/order independent
        return self.split_index == other.split_index and self.split_value == other.split_value and self.left == other.left and self.right == other.right


def rotate_coords(coords: tuple[float, ...], new_first: int) -> list[float]:
    """ Rotate the coordinates such that the entry at index new_first becomes the first element. """
    l = len(coords)
    return [coords[(i + new_first) % l] for i in range(0, l)]


def dist_sq_points(p1: tuple[float, ...], p2: tuple[float, ...]):
    return sum(((c1-c2)**2 for c1, c2 in zip(p1, p2)))


def dist_sq_point_box(p: tuple[float, ...], box_min: list[float], box_max: list[float]):
    return sum((
        (0 if bmin <= c <= bmax
         else min((c-bmin)**2, (c-bmax)**2))
        for c, bmin, bmax in zip(p, box_min, box_max)
    ))


class KDTree():
    """ KD tree class. """

    def __init__(self,
                 dimensions: int,
                 max_leaf: int,
                 root: "KDNodeInternal | KDNodeLeaf | None" = None):
        self.dimensions = dimensions
        self.max_leaf = max_leaf
        self.root = root

    def __repr__(self):
        return f"KDTree({self.dimensions!r}, {self.max_leaf!r}, {self.root!r})"

    def __eq__(self, other):
        if not isinstance(other, KDTree):
            return False
        # not structure/order independent
        return self.dimensions == other.dimensions and self.max_leaf == other.max_leaf and self.root == other.root

    def insert(self, coords: tuple[float, ...], value):
        """ Insert the given coords and value into the tree. If the coordinate is already in the tree, the new value is added to the list in the KDDatum. """

        if len(coords) != self.dimensions:
            raise Exception(
                f"Coordinates {coords} had incorrect number of dimensions, expected {self.dimensions}")

        def _insert(root: "KDNodeInternal | KDNodeLeaf | None"):
            if root is None:
                return KDNodeLeaf([KDDatum(coords, [value])])

            if isinstance(root, KDNodeInternal):
                if coords[root.split_index] >= root.split_value:
                    root.right = _insert(root.right)
                else:
                    root.left = _insert(root.left)
                root.update_bounding_box()
                return root
            else:
                # assert isinstance(root, KDNodeLeaf)
                for datum in root.data:
                    if datum.coords == coords:
                        datum.values.append(value)
                        return root

                root.data.append(KDDatum(coords, [value]))
                if len(root.data) <= self.max_leaf:
                    root.update_bounding_box()
                    return root
                else:
                    # split
                    split_index = -1
                    max_spread = -math.inf
                    for c in range(0, self.dimensions):
                        c_list = [d.coords[c] for d in root.data]
                        spread = max(c_list) - min(c_list)
                        if spread > max_spread:
                            max_spread = spread
                            split_index = c
                    assert split_index >= 0
                    # sort by rotated coordinate list so that split_index is first
                    root.data.sort(key=lambda d: rotate_coords(
                        d.coords, split_index))
                    mid = len(root.data)//2
                    if len(root.data) % 2 == 1:
                        split_value = root.data[mid].coords[split_index]
                    else:
                        split_value = (
                            root.data[mid-1].coords[split_index] + root.data[mid].coords[split_index])/2
                    # at the cost of balance and/or potential split failure, keep the splitting condition consistent
                    while mid > 0 and root.data[mid-1].coords[split_index] == split_value:
                        mid -= 1
                    if mid == 0:
                        # split failure, everything to left had same split value
                        # todo
                        root.update_bounding_box()
                        return root
                    left = KDNodeLeaf(root.data[:mid])
                    right = KDNodeLeaf(root.data[mid:])
                    return KDNodeInternal(split_index, split_value, left, right)

        self.root = _insert(self.root)

    def delete(self, coords: tuple[float, ...], value):
        if len(coords) != self.dimensions:
            raise Exception(
                f"Coordinates {coords} had incorrect number of dimensions, expected {self.dimensions}")

        def _delete(root: "KDNodeInternal | KDNodeLeaf"):
            if isinstance(root, KDNodeInternal):
                if coords[root.split_index] >= root.split_value:
                    right = _delete(root.right)
                    if right is None:
                        return root.left
                    root.right = right
                else:
                    left = _delete(root.left)
                    if left is None:
                        return root.right
                    root.left = left
            else:
                # assert isinstance(root, KDNodeLeaf)
                for i in range(0, len(root.data)):
                    if coords == root.data[i].coords:
                        root.data[i].values.remove(value)
                        if len(root.data[i].values) == 0:
                            root.data = root.data[:i] + root.data[i+1:]
                        break
                if len(root.data) == 0:
                    return None
            root.update_bounding_box()
            return root

        if self.root is None:
            return
        self.root = _delete(self.root)

    def nearest(self, coords: tuple[float, ...], count: int) -> list[KDDatum]:
        """ Find the k nearest neighbors to the coords. Undefined result if the tree contains fewer than count KDData. """

        if len(coords) != self.dimensions:
            raise Exception(
                f"Coordinates {coords} had incorrect number of dimensions, expected {self.dimensions}")

        if not self.root:
            # empty tree
            return []

        nearest: list[KDDatum] = [
            KDDatum((math.inf,) * self.dimensions, [])]

        def _nearest(root: "KDNodeInternal | KDNodeLeaf"):
            nonlocal nearest
            if isinstance(root, KDNodeInternal):
                left_d2 = dist_sq_point_box(
                    coords, root.left.bounding_box_min, root.left.bounding_box_max)
                right_d2 = dist_sq_point_box(
                    coords, root.right.bounding_box_min, root.right.bounding_box_max)

                if left_d2 <= right_d2:
                    close_d2 = left_d2
                    close_child = root.left
                    far_d2 = right_d2
                    far_child = root.right
                else:
                    close_d2 = right_d2
                    close_child = root.right
                    far_d2 = left_d2
                    far_child = root.left

                farthest = dist_sq_points(coords, nearest[-1].coords)
                if close_d2 <= farthest:
                    # need to consider =
                    _nearest(close_child)

                farthest = dist_sq_points(coords, nearest[-1].coords)
                if far_d2 <= farthest:
                    _nearest(far_child)
            else:
                # assert isinstance(root, KDNodeLeaf)
                nearest = nearest + root.data
                nearest.sort(key=lambda d: (
                    dist_sq_points(d.coords, coords), d.values))
                nearest = nearest[:count]

        _nearest(self.root)
        return nearest

    def within_distance(self, coords: tuple[float, ...], distance: float) -> list[KDDatum]:
        """ Find the k nearest neighbors to the coords. Undefined result if the tree contains fewer than count KDData. """

        if len(coords) != self.dimensions:
            raise Exception(
                f"Coordinates {coords} had incorrect number of dimensions, expected {self.dimensions}")

        if not self.root:
            # empty tree
            return []

        distance_sq = distance**2

        within_distance: list[KDDatum] = []

        def _within_distance(root: "KDNodeInternal | KDNodeLeaf"):
            nonlocal within_distance
            if isinstance(root, KDNodeInternal):
                left_d2 = dist_sq_point_box(
                    coords, root.left.bounding_box_min, root.left.bounding_box_max)
                right_d2 = dist_sq_point_box(
                    coords, root.right.bounding_box_min, root.right.bounding_box_max)

                if left_d2 <= distance_sq:
                    # need to consider =
                    _within_distance(root.left)

                if right_d2 <= distance_sq:
                    _within_distance(root.right)
            else:
                # assert isinstance(root, KDNodeLeaf)
                within_distance += [d for d in root.data if dist_sq_points(
                    coords, d.coords) <= distance_sq]

        _within_distance(self.root)
        return within_distance


if __name__ == "__main__":

    def validate_kd_structure(kd: KDTree) -> list[KDDatum]:
        def _validate(node: "KDNodeInternal | KDNodeLeaf | None", depth: int = 0) -> tuple[list[KDDatum], int]:
            if not node:
                return [], -1
            if isinstance(node, KDNodeInternal):
                left_data, left_max_depth = _validate(node.left, depth+1)
                right_data, right_max_depth = _validate(node.right, depth+1)

                # check splitting condition
                for d in left_data:
                    assert d.coords[node.split_index] < node.split_value, (
                        node.split_index, node.split_value, d)
                for d in right_data:
                    assert d.coords[node.split_index] >= node.split_value, (
                        node.split_index, node.split_value, d)

                # make sure all coordinates are unique
                all_data = left_data + right_data
                assert len(set(d.coords for d in all_data)) == len(all_data)

                return all_data, max(left_max_depth, right_max_depth)
            else:
                # make sure all coordinates are unique
                # no <= kd.max_leaf check in case of split failures
                assert len(set(d.coords for d in node.data)
                           ) == len(node.data), (kd.max_leaf, node.data)
                return node.data, depth
        data, max_depth = _validate(kd.root)
        print(f"Max depth {max_depth}")
        return data

    def random_coords(dimensions: int):
        coords = []
        for _ in range(0, dimensions):
            coords.append(random.randint(-5, 5))
        return tuple(coords)

    def random_string():
        s = ""
        for _ in range(0, 4):
            s += chr(random.randrange(0, 26) + 97)
        return s

    def random_kd(dimensions: int, max_leaf: int, size: int):
        kd = KDTree(dimensions, max_leaf)

        expected_values: dict[tuple[int, ...], list[str]] = {}

        for _ in range(0, 2*size):
            c = random_coords(dimensions)
            s = random_string()

            kd.insert(c, s)

            if not c in expected_values:
                expected_values[c] = []
            expected_values[c].append(s)

        for _ in range(0, size):
            c = lists.random_from(expected_values)
            s = lists.random_from(expected_values[c])

            kd.delete(c, s)

            expected_values[c].remove(s)
            if not expected_values[c]:
                del expected_values[c]

        return kd, expected_values

    for _ in range(0, 10):
        for size in range(0, 1000, 20):
            print(f"Size {size}")
            kd, expected_values = random_kd(
                random.randint(1, 5), random.randint(1, 5), size)

            actual = validate_kd_structure(kd)

            for d in actual:
                actual_counts = lists.count(d.values)
                expected_counts = lists.count(
                    expected_values[d.coords])
                assert actual_counts == expected_counts, (
                    actual_counts, expected_counts)

            for _ in range(0, 5):
                c = random_coords(kd.dimensions)
                count = random.randrange(1, 10)

                nearest = kd.nearest(c, count)

                if size == 0:
                    assert nearest == []
                    continue

                # in case of ties for last, the returned data are arbitrary, so for correctness just need to ensure none missed with a better distance
                farthest_distance = max(dist_sq_points(c, d.coords)
                                        for d in nearest)

                nearest_coords = set(d.coords for d in nearest)
                # coordinate collisions may make smaller tree than count for small trees
                assert len(nearest_coords) <= count, (c, count,
                                                      nearest, kd)
                for coords in expected_values:
                    if dist_sq_points(c, coords) < farthest_distance:
                        assert coords in nearest_coords, (c,
                                                          coords, nearest_coords)

            for _ in range(0, 5):
                c = random_coords(kd.dimensions)
                distance = random.randrange(1, 10)

                within = kd.within_distance(c, distance)

                if size == 0:
                    assert within == []
                    continue

                within_coords = {d.coords for d in within}
                for coords in expected_values:
                    assert (dist_sq_points(c, coords) <= (
                        distance ** 2)) == (coords in within_coords), (c, coords, dist_sq_points(c, coords), distance**2, within_coords, kd)
