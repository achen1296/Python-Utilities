def egcd(a: int, b: int) -> tuple[int, int, int]:
    prev_x, x = 1, 0
    prev_y, y = 0, 1
    while b != 0:
        q = a//b
        a, b = b, a % b
        prev_x, x = x, prev_x-q*x
        prev_y, y = y, prev_y-q*y
    return (prev_x, prev_y, a)


def mod_inverse(i: int, N: int) -> int:
    x, y, g = egcd(i, N)
    return x % N


def mod_exp(i: int, pow: int, N: int) -> int:
    if pow == 0:
        return 1
    if pow < 0:
        pow *= -1
        i = mod_inverse(i, N)
    r = 1
    while pow > 1:
        if pow % 2 == 0:
            i = (i*i) % N
            pow //= 2
        else:
            r = (r*i) % N
            pow -= 1
    return (i * r) % N
