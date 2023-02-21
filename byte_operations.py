from __future__ import annotations
import random


def hex_to_ints(hex: str) -> list[int]:
    return [b for b in bytes.fromhex(hex)]


def ints_to_hex(ints: list[int]) -> str:
    return bytes(ints).hex()


def plain_to_ints(plaintext: str) -> list[int]:
    return [ord(c) for c in plaintext]


def ints_to_plain(ints: list[int]) -> str:
    return "".join([chr(i) for i in ints])


def plain_to_hex(plaintext: str) -> str:
    return bytes(plaintext, encoding="ascii").hex()


def hex_to_plain(hex: str) -> str:
    return ints_to_plain(hex_to_ints(hex))


def xor(*int_lists: list[int]) -> list[int]:
    """ If the lists are of unequal size, shorter ones are cycled. """
    max_len = max(len(l) for l in int_lists)
    result = [0 for _ in range(0, max_len)]
    for l in int_lists:
        len_l = len(l)
        result = [result[i] ^ l[i % len_l] for i in range(0, max_len)]
    return result


def random_bytes(length: int):
    b = bytearray(length)
    for i in range(0, length):
        b[i] = random.randint(0, 255)
    return b


def get_bit(x: int, index: int):
    assert 0 <= x < 256
    assert 0 <= index < 8
    x >>= (7-index)
    return x % 2


def set_bit(x: int, index: int, bit: int) -> int:
    assert 0 <= x < 256
    assert 0 <= index < 8
    assert 0 <= bit <= 1

    if bit == 0:
        return x & (255 - (1 << (7-index)))
    else:
        return x | (1 << (7-index))


def bit_string(x: bytes) -> str:
    byte_strings = []
    for i in range(0, len(x)):
        s = ""
        for j in range(0, 8):
            s += str(get_bit(x[i], j))
        byte_strings.append(s)
    return " ".join(byte_strings)
