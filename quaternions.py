from numbers import Number

import numpy as np

i = 1j

REAL_MATRIX = np.array([
    [1, 0],
    [0, 1]
])
I_MATRIX = np.array([
    [i, 0],
    [0, -i]
])
J_MATRIX = np.array([
    [0, 1],
    [-1, 0]
])
K_MATRIX = np.array([
    [0, i],
    [i, 0]
])
PART_MATRICES = (REAL_MATRIX, I_MATRIX, J_MATRIX, K_MATRIX)


class Quaternion:
    def __init__(self, real, i, j, k):
        self._real = real
        self._i = i
        self._j = j
        self._k = k
        self._parts = [real, i, j, k]

    @property
    def real(self):
        return self._real

    @real.setter
    def real(self, value):
        self._real = value
        self._parts[0] = value

    @property
    def i(self):
        return self._i

    @i.setter
    def i(self, value):
        self._i = value
        self._parts[1] = value

    @property
    def j(self):
        return self._j

    @j.setter
    def j(self, value):
        self._j = value
        self._parts[1] = value

    @property
    def k(self):
        return self._k

    @k.setter
    def k(self, value):
        self._k = value
        self._parts[1] = value

    @staticmethod
    def from_matrix(m: np.ndarray):
        """ Does not ensure the matrix is actually a valid quaternion! """
        return Quaternion(np.real(m[0, 0]), np.imag(m[0, 0]), np.real(m[0, 1]), np.imag(m[0, 1]))

    def as_matrix(self):
        return np.sum((p * M for p, M in zip(self._parts, PART_MATRICES)))

    def inverse(self):
        mag_sq = sum(p**2 for p in self._parts)
        return Quaternion(self._real/mag_sq, -self._i/mag_sq, -self._j/mag_sq, -self._k/mag_sq)

    def __eq__(self, other) -> bool:
        return isinstance(other, Quaternion) and self._real == other._real and self._i == other._i and self._j == other._j and self._k == other._k

    def __hash__(self):
        return hash(self._parts)

    def __neg__(self):
        return Quaternion(*(-p for p in self._parts))

    def __add__(self, other: "Quaternion"):
        return Quaternion(*(p1+p2 for p1, p2 in zip(self._parts, other._parts)))

    def __sub__(self, other: "Quaternion"):
        return Quaternion(*(p1-p2 for p1, p2 in zip(self._parts, other._parts)))

    def __mul__(self, other: "Quaternion | Number"):
        if isinstance(other, Number):
            return Quaternion(*(p*other for p in self._parts))
        else:
            return Quaternion.from_matrix(self.as_matrix() @ other.as_matrix())

    def __div__(self, other: "Quaternion|Number"):
        if isinstance(other, Number):
            return self * 1/other
        else:
            return self * other.inverse()

    def __pow__(self, exponent: int):
        if not isinstance(exponent, int):
            raise TypeError("exponent must be an integer")
        if exponent == 0:
            return Quaternion(1, 0, 0, 0)
        if exponent < 0:
            q = self.inverse()
            exponent *= -1
        else:
            q = self
        acc = q
        while exponent > 1:
            if exponent % 2 == 1:
                acc *= q
                exponent -= 1
            else:
                acc *= acc
                exponent //= 2
        return acc

    def __str__(self):
        return f"{self._real} + {self._i}i + {self._j}j + {self._k}k"

    def __repr__(self):
        return f"Quaternion({self.real}, {self.i}, {self.j}, {self.k})"
