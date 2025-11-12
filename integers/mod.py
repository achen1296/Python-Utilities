# (c) Andrew Chen (https://github.com/achen1296)

def _gcd(a: int, b: int) -> tuple[int, int, int]:
    # https://en.wikipedia.org/wiki/Extended_Euclidean_algorithm for modular inverse
    prev_x, x = 1, 0
    prev_y, y = 0, 1
    while b != 0:
        q = a//b
        a, b = b, a % b
        prev_x, x = x, prev_x-q*x
        prev_y, y = y, prev_y-q*y
    return (prev_x, prev_y, a)

def gcd(a:int, b:int):
    return _gcd(a, b)[2]

def inverse(i: int, N: int) -> int:
    x, y, g = _gcd(i, N)
    return x % N


def exp(i: int, pow: int, N: int) -> int:
    if pow == 0:
        return 1
    if pow < 0:
        pow *= -1
        i = inverse(i, N)
    r = 1
    while pow > 1:
        if pow % 2 == 0:
            i = (i*i) % N
            pow //= 2
        else:
            r = (r*i) % N
            pow -= 1
    return (i * r) % N


def in_range(i: int, lower: int, upper: int, modulus: int):
    i -= lower
    upper -= lower
    i %= modulus
    upper %= modulus
    return 0 <= i <= upper
