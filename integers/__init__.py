from typing import Iterable

import lists

import mod


def primes(max: int | None = None):
    # this is fast enough for "small" numbers (e.g. on order of millions)
    def prime_candidates():
        yield 2
        yield 3
        # n = 1
        n = 5
        while True:
            # yield 6 * n - 1
            # yield 6 * n + 1
            # n += 1
            # equivalent to the above but no multiplication
            yield n
            n += 2
            yield n
            n += 4

    def divisible_by_any(num: int, factors: list[int]):
        for f in factors:
            if num % f == 0:
                return True
            if f * f > num:
                break
        return False

    primes = []
    for p in prime_candidates():
        if max is not None and p > max:
            break
        if not divisible_by_any(p, primes):
            primes.append(p)
            yield p


def sieve(numbers: Iterable[int]) -> Iterable[int]:
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
    if x <= 0:
        raise Exception("Positive values only")

    if x == 1:
        return []

    ps = primes(x//2)

    factors = []

    for p in ps:
        while x % p == 0:
            factors.append(p)
            x //= p
        if x == 1:
            break

    if len(factors) == 0:
        return [x]

    return factors


def totient(x: int) -> int:
    result = 1
    factors = lists.count(factor(x))
    for p in factors:
        e = factors[p]
        result *= (p-1) * (p**(e-1))
    return result


def divisors(x: int) -> Iterable[int]:
    factor_power = lists.count(factor(x))
    factors = list(factor_power)

    def _divisors(factors: list[int]):
        if factors == []:
            yield 1
            return
        f = factors[0]
        for i in range(0, factor_power[f]+1):
            fi = (f**i)
            yield from (fi * d for d in _divisors(factors[1:]))

    return _divisors(factors)


def int_input(prompt: str, min: int | None = None, max: int | None = None, default: int | None = None):
    while True:
        try:
            t = input(prompt)
            if default is not None and not t.strip():
                return default
            n = int(t)
        except ValueError:
            print("Invalid integer")
            continue
        if (min is None or min <= n) and (max is None or n <= max):
            return n
        else:
            print(f"Expected number {", ".join([
                "" if min is None else f"at least {min}",
                "" if max is None else f"at most {max}"
            ])}")
