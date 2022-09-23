def primes(max: int):
    primes = list(range(2, max+1))
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
