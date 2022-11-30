import typing


class Polynomial:
    @staticmethod
    def __remove_high_exp_zeros(coefficients: typing.Iterable[float]):
        coefficients = list(coefficients)
        l = len(coefficients)
        if l == 0:
            return coefficients
        zeros = 0
        while zeros < l and coefficients[l-zeros-1] == 0:
            zeros += 1
        return coefficients[:l-zeros]

    def __init__(self, *coefficients: float, high_powers_first=True):
        if high_powers_first:
            coefficients = reversed(coefficients)
        self.coefficients: list[float] = Polynomial.__remove_high_exp_zeros(
            coefficients)

    @classmethod
    def term(cls, c: float, e: int):
        coeffs = [0 for _ in range(0, e+1)]
        coeffs[0] = c
        return cls(*coeffs)

    def is_zero(self):
        for c in self.coefficients:
            if c != 0:
                return False
        return True

    def __len__(self):
        return len(self.coefficients)

    def degree(self):
        return len(self) - 1

    def __getitem__(self, e: int):
        if e < 0:
            raise Exception("No negative exponents")
        l = len(self)
        if e >= l:
            return 0
        return self.coefficients[e]

    def reduce(self, modulus: int):
        self.coefficients = Polynomial.__remove_high_exp_zeros(
            [c % modulus for c in self.coefficients])

    def __lt__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd < od:
            return True
        elif sd > od:
            return False
        for i in range(sd, 0-1, -1):
            if self[i] < other[i]:
                return True
            if self[i] > other[i]:
                return False
        return False

    def __le__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd < od:
            return True
        elif sd > od:
            return False
        for i in range(sd, 0-1, -1):
            if self[i] < other[i]:
                return True
            if self[i] > other[i]:
                return False
        return True

    def __gt__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd > od:
            return True
        elif sd < od:
            return False
        for i in range(sd, 0-1, -1):
            if self[i] > other[i]:
                return True
            if self[i] < other[i]:
                return False
        return False

    def __ge__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd > od:
            return True
        elif sd < od:
            return False
        for i in range(sd, 0-1, -1):
            if self[i] > other[i]:
                return True
            if self[i] < other[i]:
                return False
        return True

    def __eq__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd != od:
            return False
        for i in range(0, len(self)):
            if self[i] != other[i]:
                return False
        return True

    def __ne__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd != od:
            return True
        for i in range(0, len(self)):
            if self[i] != other[i]:
                return True
        return False

    def __neg__(self) -> "Polynomial":
        return Polynomial(*(-self[i] for i in range(0, len(self))), high_powers_first=False)

    def __add__(self, other: "Polynomial") -> "Polynomial":
        l = max(len(self), len(other))

        return Polynomial(*(self[i] + other[i] for i in range(0, l)), high_powers_first=False)

    def __sub__(self, other: "Polynomial") -> "Polynomial":
        l = max(len(self), len(other))

        return Polynomial(*(self[i] - other[i] for i in range(0, l)), high_powers_first=False)

    def __mul__(self, other: "Polynomial") -> "Polynomial":
        l1 = len(self)
        l2 = len(other)
        # deg(p1) = l1 - 1
        # deg(p2) = l2 - 1
        # deg(p1 * p2) = deg(p1) + deg(p2) = l1 + l2 - 2 = len(p1 * p2) - 1
        new_coeff = [0 for i in range(0, l1 + l2 - 1)]
        for e1 in range(0, l1):
            for e2 in range(0, l2):
                new_coeff[e1 + e2] += self[e1] * other[e2]
        return Polynomial(*new_coeff, high_powers_first=False)

    def __floordiv__(self, other: "Polynomial") -> "Polynomial":
        q, _ = divmod(self, other)
        return q

    def __mod__(self, other: "Polynomial") -> "Polynomial":
        _, r = divmod(self, other)
        return r

    def __divmod__(self, other: "Polynomial") -> tuple["Polynomial", "Polynomial"]:
        od = other.degree()

        # self = q * other + r
        q = Polynomial(0)
        r = self

        rd = r.degree()
        while rd >= od:
            c = Polynomial.term(r[rd] / other[od], rd - od)
            q += c
            r -= c * other
            rd = r.degree()

        return (q, r)

    @staticmethod
    def gcd(p1: "Polynomial", p2: "Polynomial", modulus: int = None) -> "Polynomial":
        # p1 = q * p2 + r
        if modulus is not None:
            p1.reduce(modulus)
            p2.reduce(modulus)
        dividend, divisor = max(p1, p2), min(p1, p2)
        r = p2
        while True:
            _, r = divmod(dividend, divisor)
            if modulus is not None:
                r.reduce(modulus)
            if r.is_zero():
                return divisor
            dividend = divisor
            divisor = r

    def __str__(self):
        if self.is_zero():
            return "0"

        l = len(self)
        s = ""
        first = True
        e = l - 1
        while e >= 0:
            c = self.coefficients[e]
            if c != 0:
                if first:
                    first = False
                else:
                    s += " + "
                if c != 1 or e == 0:
                    s += f"{c}"
                if e > 1:
                    s += f"x^{e}"
                if e == 1:
                    s += "x"
            e -= 1
        return s

    def __repr__(self):
        return f"Polynomial({','.join(reversed([str(c) for c in self.coefficients]))})"
