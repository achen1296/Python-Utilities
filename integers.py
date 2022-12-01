import lists
import math
import typing


def primes(max: int):
    def gen_prime_candidates():
        yield 2
        yield 3
        n = 1
        while True:
            yield 6 * n - 1
            yield 6 * n + 1
            n += 1

    def divisible_by_any(num: int, factors: list[int]):
        for f in factors:
            if num % f == 0:
                return True
        return False

    primes = []
    for p in gen_prime_candidates():
        if p > max:
            break
        if not divisible_by_any(p, primes):
            primes.append(p)
            yield p


def sieve(numbers: typing.Iterable[int]) -> typing.Iterable[int]:
    numbers = sorted(numbers)
    if len(numbers) == 0:
        return []
    max = numbers[-1]

    i = 0
    while i < len(numbers):
        curr_prime = numbers[i]

        yield curr_prime

        if curr_prime > max//2:
            # above max//2, sieving will not remove any more composite numbers; yield the rest
            i += 1
            break

        j = i + 1
        while j < len(numbers):
            if numbers[j] % curr_prime == 0:
                del numbers[j]
            else:
                j += 1

        i += 1

    lp = len(numbers)
    while i < lp:
        yield numbers[i]
        i += 1


def factor(x: int) -> list[int]:
    ps = primes(x//2)

    factors = []

    for p in ps:
        while x % p == 0:
            factors.append(p)
            x /= p
        if x == 1:
            break

    if len(factors) == 0:
        return [x]

    return factors


def totient(x: int) -> int:
    result = 1
    fact = lists.count(factor(x))
    for p in fact:
        e = fact[p]
        result *= (p-1) * (p**(e-1))
    return result
