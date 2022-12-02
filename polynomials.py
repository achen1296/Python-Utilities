import re
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

    @staticmethod
    def coefficients_from_str(s: str):
        # remove whitespace
        s = re.sub("\s+", "", s)
        # split around +/- operations but keep them on the split terms
        terms = re.split("(?=[-+])", s)
        # remove empty strings
        terms = [t for t in terms if len(t) > 0]
        coefficients = []
        exponents = []
        for t in terms:
            match: re.Match = re.match(
                "^([-+])?((\d+)|(\d*\.\d+)|(\d+\.))?\*?(x((\^|\*\*)(\d+))?)?$", t)
            # group 1: sign, defaults to +
            # group 2: optional coefficient, contains 3-5, defaults to 1
            # group 3: integer coefficient
            # group 4, 5: float coefficient
            # group 6: optional "x" + contains group 7, defaults to x^0 = 1
            # group 7: optional "^" or "**" + contains group 9, defaults to x = x^1
            # group 9: integer exponent
            # must have either group 2 or group 6

            if not match or not (match.group(2) or match.group(6)):
                raise Exception("Invalid Polynomial string")

            if match.group(1) == "-":
                sign = -1
            else:
                sign = 1
            if match.group(2):
                int_coeff = match.group(3)
                if int_coeff:
                    coefficients.append(sign*int(int_coeff))
                else:
                    float_coeff = match.group(4) or match.group(5)
                    coefficients.append(sign*float(float_coeff))
            else:
                coefficients.append(1)
            if match.group(6):
                if match.group(7):
                    exponents.append(int(match.group(9)))
                else:
                    exponents.append(1)
            else:
                exponents.append(0)
        degree = max(exponents)
        combined_coeff = [0 for _ in range(0, degree+1)]
        for c, e in zip(coefficients, exponents):
            combined_coeff[e] += c
        return combined_coeff

    def __init__(self, *coefficients: typing.Union[float, str], high_powers_first=True):
        """Specify coefficients in order from high to low exponent.

        Alternatively, specify a single str argument with the variable x. Supports optional * between coefficients and the variable x. Both ^ and ** may be used for exponentiation.

        For example, Polynomial(1,2,3) == Polynomial("x^2+2x+3")."""
        if len(coefficients) == 1 and isinstance(coefficients[0], str):
            coefficients = Polynomial.coefficients_from_str(coefficients[0])
        elif high_powers_first:
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

    def __iter__(self):
        return iter(self.coefficients)

    def __reversed__(self):
        return reversed(self.coefficients)

    def __lt__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd != od:
            return sd < od
        return tuple(reversed(self.coefficients)) < tuple(reversed(other.coefficients))

    def __le__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd != od:
            return sd < od
        return tuple(reversed(self.coefficients)) <= tuple(reversed(other.coefficients))

    def __gt__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd != od:
            return sd > od
        return tuple(reversed(self.coefficients)) > tuple(reversed(other.coefficients))

    def __ge__(self, other: "Polynomial") -> bool:
        sd = self.degree()
        od = other.degree()
        if sd != od:
            return sd > od
        return tuple(reversed(self.coefficients)) >= tuple(reversed(other.coefficients))

    def __eq__(self, other: "Polynomial") -> bool:
        return tuple(self.coefficients) == tuple(other.coefficients)

    def __ne__(self, other: "Polynomial") -> bool:
        return tuple(self.coefficients) != tuple(other.coefficients)

    def __hash__(self):
        return hash(tuple(self.coefficients))

    def __neg__(self) -> "Polynomial":
        return Polynomial(*(-self[e] for e in range(0, len(self))), high_powers_first=False)

    def __add__(self, other: "Polynomial") -> "Polynomial":
        l = max(len(self), len(other))

        return Polynomial(*(self[e] + other[e] for e in range(0, l)), high_powers_first=False)

    def __sub__(self, other: "Polynomial") -> "Polynomial":
        l = max(len(self), len(other))

        return Polynomial(*(self[e] - other[e] for e in range(0, l)), high_powers_first=False)

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

    def __mod__(self, other: typing.Union["Polynomial", int]) -> "Polynomial":
        if isinstance(other, Polynomial):
            _, r = divmod(self, other)
            return r
        elif isinstance(other, int):
            return Polynomial(*[c % other for c in self.coefficients], high_powers_first=False)

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
            p1 %= modulus
            p2 %= modulus
        dividend, divisor = max(p1, p2), min(p1, p2)
        r = p2
        while True:
            r = dividend % divisor
            if modulus is not None:
                r %= modulus
            if r.is_zero():
                return divisor
            dividend = divisor
            divisor = r

    def evaluate(self, x: float, modulus: int = None):
        result = 0
        for e in range(0, len(self)):
            result += self[e] * (x ** e)
            if modulus is not None:
                result %= modulus
        return result

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
