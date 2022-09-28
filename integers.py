import math
import typing


def sieve(numbers: typing.Union[int, typing.Iterable[int]]) -> list[int]:
    if isinstance(numbers, int):
        max = numbers
        primes = list(range(2, numbers+1))
    else:
        primes = sorted(numbers)
        if len(primes) == 0:
            return []
        max = primes[-1]

    i = 0
    while i < len(primes):
        curr_prime = primes[i]

        if curr_prime > max//2:
            break

        j = i + 1
        while j < len(primes):
            if primes[j] % curr_prime == 0:
                del primes[j]
            else:
                j += 1

        i += 1

    return primes


def factor(x: int) -> list[int]:
    primes = sieve(math.floor(math.sqrt(x)))

    factors = []

    for p in primes:
        while x % p == 0:
            factors.append(p)
            x /= p
        if x == 1:
            break

    if len(factors) == 0:
        return [x]

    return factors
