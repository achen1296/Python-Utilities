import random
from typing import Iterable, Sequence


def random_from[T](iter: Iterable[T]) -> T:
    return sample(iter, 1)[0]


def sample[T](iter: Iterable[T], k: int) -> list[T]:
    """ If `it` is a `Sequence`, it will be faster -- the length is known in advance and an arbitrary element can be indexed.

    If not, then will still correctly return a sample from `it` without needing to know its length in advance, but this requires more `random` calls. Additionally, `it` will be consumed completely if it is an iterator rather than an iterable. """
    if isinstance(iter, Sequence):
        return random.sample(iter, k)
    else:
        if k < 0:
            # same error message as random.sample
            raise ValueError("Sample larger than population or is negative")

        if k == 0:
            return []

        i = -1
        sample: list[T] = []

        enumerated = enumerate(iter)

        # consume first k elements and add them to the sample with 100% probability
        for _ in range(0, k):
            try:
                sample.append(next(enumerated)[1])
            except StopIteration:
                # same error message as random.sample
                raise ValueError("Sample larger than population or is negative")

        for i, e in enumerated:
            """ Now we assume we have a random sample of `k` elements out of the first `i` (index is the same as the number of elements before this one) and we convert it to a random sample of `k` elements out of the first `i+1` elements by swapping out a random one of the elements of the existing sample with this one with probability `k/(i + 1)`. """
            if random.randrange(0, i+1) < k:
                sample[random.randrange(0, k)] = e

        return sample


if __name__ == "__main__":
    counts = {}
    test_iterations = int(1e6)
    k = 5
    for _ in range(0, test_iterations):
        for e in sample(range(0, 100), k):
            counts[e] = counts.get(e, 0)+1
    print(sorted(counts.values()))
    s = sum(counts.values())
    assert s == test_iterations * k, s
