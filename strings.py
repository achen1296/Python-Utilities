import re
import typing


def unescape(s: str, *, escape_char: str = "\\") -> str:
    """Removes one level of escape characters. Only supports single characters."""
    if len(escape_char) != 1:
        raise Exception("Only single characters allowed")
    i = 0
    while i < len(s):
        if s[i] == escape_char:
            s = s[:i] + s[i+1:]
        # if there was an escape \, this skips over the character after it, in case it is an escaped \ i.e. \\, so only the first one is removed
        i += 1
    return s


def escape(s: str, special_chars: typing.Iterable[str], *, escape_char: str = "\\") -> str:
    """Adds one level of escape characters. Only supports single characters."""
    for c in special_chars:
        if len(c) != 1:
            raise Exception("Only single characters allowed")
    i = 0
    while i < len(s):
        if s[i] in special_chars:
            s = s[:i]+escape_char+s[i:]
            i += 1
        i += 1
    return s


def argument_split(s: str, *, sep: str = "\s+", pairs: dict[str, str] = None, ignore_internal_pairs: typing.Iterable[str] = None, remove_outer: dict[str, str] = {'"': '"', "'": "'"}, remove_empty_tokens=True, unescape_char="\\", re_flags: int = 0) -> list[str]:
    """ Like str's regular split method, but accounts for arguments that contain the split separator if they occur in compounds (for example, spaces in quoted strings should not result in a split for the default arguments). Arguments for `pairs` and `ignore_internal_pairs` are passed to `find_pairs`. """

    # spans that match the separator and that are not also inside of pairs
    splits: list[tuple[int, int]] = []

    found_pairs = find_pairs(
        s, pairs=pairs, ignore_internal_pairs=ignore_internal_pairs)

    def in_any_pair(span: tuple[int, int]):
        # only outermost pairs matter
        for p in found_pairs:
            if span_include_inclusive(p.span(), span):
                return True
        return False

    for m in re.finditer(sep, s, re_flags):
        if not in_any_pair(m.span()):
            splits.append(m.span())

    # convert splits, i.e. slices to exclude, into slices to include
    slices = [0]
    for sp in splits:
        slices.append(sp[0])
        slices.append(sp[1])
    slices.append(len(s))

    tokens = [s[slices[i]:slices[i+1]] for i in range(0, len(slices), 2)]
    if remove_empty_tokens:
        tokens = [t for t in tokens if t != ""]
    if unescape_char != None:
        tokens = [unescape(t, escape_char=unescape_char) for t in tokens]
    if remove_outer != None and len(remove_outer) > 0:
        new_tokens = []
        for t in tokens:
            for o in remove_outer:
                m = re.match(o, t)
                if m != None:
                    # remove start
                    t = t[m.end():]
                    # remove end (last occurence)
                    for m in re.finditer(remove_outer[o], t):
                        last_match = m
                    if last_match.end() < len(t):
                        raise Exception(
                            f"While removing outer pair, pair end <{last_match}> was not actually last found at the end of the token <{t}>")
                    t = t[:m.start()]
                    # only remove one outer pair
                    break
            new_tokens.append(t)
        tokens = new_tokens
    return tokens


def next_match(regular_expressions: typing.Iterable[str], s: str, *, no_overlap=False, flags=0) -> typing.Generator[tuple[str, re.Match], None, None]:
    """ Generates tuples containing the regular expression that next matches earliest in the string (if start indices tie, earliest end is first) and the match object it produces. """
    # initialize iters
    iters = {}
    for r in regular_expressions:
        iters[r] = re.finditer(r, s, flags)

    empty_iters = set()
    # get first element from each iter
    matches = {}
    for r in iters:
        try:
            matches[r] = next(iters[r])
        except StopIteration:
            empty_iters.add(r)
    for r in empty_iters:
        del iters[r]

    prev_end = -1
    while len(iters) > 0:
        # length of s is max possible value
        next_start = len(s)+1
        next_end = len(s)+1
        # find earliest match
        for r, match in matches.items():
            m_start, m_end = match.span()
            if m_start < next_start or (m_start == next_start and m_end < next_end):
                next_start = m_start
                next_end = m_end
                next_r = r
                next_match = match
        try:
            matches[next_r] = next(iters[next_r])
        except StopIteration:
            del matches[next_r]
            del iters[next_r]
        # first condition skips empty matches
        if next_start < next_end and (not no_overlap or prev_end <= next_start):
            prev_end = next_end
            yield (next_r, next_match)


def last_match(regular_expressions: typing.Iterable[str], s: str, *, no_overlap=False, flags=0) -> typing.Generator[tuple[str, re.Match], None, None]:
    """ Generates tuples containing the regular expression that next matches latest in the string (if end indices tie, latest start is first) and the match object it produces. Unlike next_match, must store all matches at once, since regular expressions are usually evaluated left to right. """
    matches = {}
    for r in regular_expressions:
        l = list(re.finditer(r, s, flags))
        list.reverse(l)
        if l != []:
            matches[r] = l

    prev_start = len(s)+1
    while len(matches) > 0:
        last_start = -1
        last_end = -1
        for r, match_list in matches.items():
            match = match_list[0]
            m_start, m_end = match.span()
            if m_end > last_end or (m_end == last_end and m_start > last_start):
                last_start = m_start
                last_end = m_end
                last_r = r
                last_match = match

        last_list = matches[last_r]
        if len(last_list) <= 1:
            del matches[last_r]
        else:
            matches[last_r] = last_list[1:]
        if last_start < last_end and (not no_overlap or last_end <= prev_start):
            prev_start = last_start
            yield(last_r, last_match)


def matches_any(regular_expressions: typing.Iterable[str], s: str, *, flags=0):
    for r in regular_expressions:
        if re.match(r, s, flags):
            return True
    return False


class NoPairException(Exception):
    pass


class Pair:
    pass


class Pair:
    def __init__(self, original_str: str, start_span: tuple[int, int], end_span: tuple[int, int], internal_pairs: typing.Iterable[Pair] = None):
        # no zero length start/end strings, therefore <, but they can be directly adjacent, therefore <=
        if not (start_span[0] < start_span[1] <= end_span[0] < end_span[1]) or start_span[0] < 0 or end_span[1] > len(original_str):
            raise Exception(f"Invalid start/end spans {start_span} {end_span}")
        self.original_str = original_str
        self.start_span = start_span
        self.end_span = end_span
        if internal_pairs == None:
            self.internal_pairs = []
        else:
            self.internal_pairs = internal_pairs

    def add_internal(self, internal: Pair):
        self.internal_pairs.append(internal)
        list.sort(self.internal_pairs)

    def span(self) -> tuple[int, int]:
        return (self.start_span[0], self.end_span[1])

    def __repr__(self) -> str:
        return "Pair("+repr(self.original_str) + "," + repr(self.start_span) + "," + repr(self.end_span) + (","+repr(self.internal_pairs) if self.internal_pairs != [] else "") + ")"

    def __str__(self) -> str:
        return "Pair " + str(self.start_span) + "-" + str(self.end_span) + " \"" + self.original_str[self.start_span[0]:self.start_span[1]] + "\" \"" + self.original_str[self.end_span[0]:self.end_span[1]] + "\"" + (","+str(self.internal_pairs) if self.internal_pairs != [] else "") + ")"

    def __lt__(self, other: Pair):
        if self.start_span[0] != other.start_span[0]:
            return self.start_span[0] < other.start_span[0]
        elif self.start_span[1] != other.start_span[1]:
            return self.start_span[1] < other.start_span[1]
        elif self.end_span[0] != other.end_span[0]:
            return self.end_span[0] < other.end_span[0]
        else:
            return self.end_span[1] < other.end_span[1]

    def __gt__(self, other: Pair):
        if self.start_span[0] != other.start_span[0]:
            return self.start_span[0] > other.start_span[0]
        elif self.start_span[1] != other.start_span[1]:
            return self.start_span[1] > other.start_span[1]
        elif self.end_span[0] != other.end_span[0]:
            return self.end_span[0] > other.end_span[0]
        else:
            return self.end_span[1] > other.end_span[1]

    def __eq__(self, other: Pair):
        return self.original_str == other.original_str and self.start_span == other.start_span and self.end_span == other.end_span and self.internal_pairs == other.internal_pairs


def span_include_inclusive(greater: tuple[int, int], lesser: tuple[int, int]):
    return greater[0] <= lesser[0] and greater[1] >= lesser[1]


def span_include_exclusive(greater: tuple[int, int], lesser: tuple[int, int]):
    return greater[0] < lesser[0] and greater[1] > lesser[1]


def find_pair(s: str, start: int, **find_pairs_kwargs):
    pairs = find_pairs(s, **find_pairs_kwargs)
    i = 0
    while i < len(pairs):
        p = pairs[i]
        if p.start_span[0] == start:
            return p.end_span[0]
        pairs.extend(p.internal_pairs)
        i += 1
    raise NoPairException(
        f"Didn't find a pair beginning at index {start} of {s}")


def find_pairs(s: str, *, pairs: dict[str, str] = None, ignore_internal_pairs: typing.Iterable[str] = None, require_balanced_pairs=True) -> list[Pair]:
    """ Finds pairs in the string of the specified expressions and returns the indices of the start and end of each pair (the first index of the matches).

    Any unbalanced pairs result in a NoPairException unless require_balanced_pairs is set to False. The expressions for pair starts and ends should not allow overlap with themselves (although pair starts and ends can be the same character, like quotes), otherwise the results are undefined.

    For example, `find_pairs("[ex(am)\\"{\\"p\\\\]le]")`:

    First, the [ is found. Then ( is found, before matching immediately with ). Then the quote is found. Since it is inside quotes, the { is ignored. The next matching quote is found. The next escaped \] is ignored, and finally the first [ is paired. Thus the complete return value is `[(0,15),(7,9),(3,6)]` -- in reverse order of the pair end index.

    If the `pairs` and `ignore_internal_pairs` parameters are left as None, unescaped {, [, (, ", and ' characters are matched with their opposites. However, `pairs` can be specified as a dictionary, with the regular expression for a pair start mapping to the regular expression for the corresponding paired character. The ignoring of escaped characters (those preceded by an \\ character) is part of the default regular expressions for `pairs`. `ignore_internal_pairs` is a set of pair starter regular expressions and is only used if `pairs` matches a piece of the string first. """

    if pairs == None:
        # negative look behind for \
        NO_ESCAPE = "(?<!\\\\)"
        pairs = {NO_ESCAPE+"\"": NO_ESCAPE+"\"", NO_ESCAPE+"'": NO_ESCAPE+"'", NO_ESCAPE+"\(": NO_ESCAPE+"\)",
                 NO_ESCAPE+"\[": NO_ESCAPE+"\]", NO_ESCAPE+"{": NO_ESCAPE+"}"}
    if ignore_internal_pairs == None:
        ignore_internal_pairs = {"\"", "\'"}

    ignore_internal_pairs = set(ignore_internal_pairs)

    pair_starts_gen = next_match(pairs, s)
    pair_ends_gen = next_match(pairs.values(), s)

    # return value, collected index pairs
    pair_list = []
    # stack of pair starts
    start_stack = []
    next_start = next(pair_starts_gen, None)
    ignoring_internal = False
    while True:
        # get the next pair end
        try:
            next_end = next(pair_ends_gen)
        except StopIteration:
            # exhausted all pair ends
            break
        # push all starts before that onto the stack, which may be none (and should be sometimes)
        while next_start != None and next_start[1].end() <= next_end[1].start():
            if not ignoring_internal:
                start_stack.append(next_start)
            if matches_any(ignore_internal_pairs, next_start[1].group()):
                # the rest of the starts up to the next end are consumed without being added to the stack
                ignoring_internal = True
            next_start = next(pair_starts_gen, None)
        # make sure the last start pushed matches
        try:
            popped_start = start_stack.pop()
        except IndexError:
            # pair match failed; attempt to interpret next end as a start instead (e.g. quotes by default)
            if next_start == None:
                if require_balanced_pairs:
                    raise NoPairException(
                        "Ran out of starts, could not reinterpret as end")
                else:
                    return pair_list
            if span_include_inclusive(next_start[1].span(), next_end[1].span()):
                continue
            if require_balanced_pairs:
                raise NoPairException(
                    f"Ran out of pair starts to match with {next_end[1]}. {pair_list} {start_stack}")
            else:
                return pair_list
        if pairs[popped_start[0]] != next_end[0]:
            if ignoring_internal:
                # try to find the internal-ignore terminating match
                # return popped pair start to stack
                start_stack.append(popped_start)
                continue
            # pair match failed; attempt to interpret next end as a start instead (e.g. quotes by default)
            if span_include_inclusive(next_start[1].span(), next_end[1].span()):
                # return popped pair start to stack
                start_stack.append(popped_start)
                continue
            # not ignoring and not also a start
            if require_balanced_pairs:
                raise NoPairException(
                    f"Pair starting {popped_start[1]} did not match with a {pairs[popped_start[0]]}, {next_end[1]} found instead\nPairs so far: {pair_list}\nStart stack: {start_stack}\nIn string: {s}")
            else:
                return pair_list
        # pair matched
        new_pair = Pair(s, popped_start[1].span(), next_end[1].span())
        # nest prior pairs inside the new one if they are included inside it
        while len(pair_list) > 0 and span_include_exclusive(new_pair.span(), pair_list[-1].span()):
            new_pair.add_internal(pair_list[-1])
            pair_list = pair_list[:-1]
        pair_list.append(new_pair)
        ignoring_internal = False
        # if end was also counted as a start, skip it
        if next_start != None and next_start[1].span() == next_end[1].span():
            next_start = next(pair_starts_gen, None)
    # did not also exhaust all pair starts
    if next_start != None and require_balanced_pairs:
        raise NoPairException(
            f"Pair starting {next_start[1]} did not match with a {pairs[next_start[0]]}, ran out of pair ends instead. {pair_list} {start_stack}")
    return pair_list


def unicode_escape(s: str):
    escaped = ""
    for c in s:
        if c.isascii():
            escaped += c
        else:
            escaped += "\\u" + hex(ord(c)).removeprefix("0x")
    return escaped


def strikethrough(s: str):
    # U+0336 "Combining Long Stroke Overlay"
    strikethrough_char = '\u0336'
    new = strikethrough_char
    for c in s:
        new += c + strikethrough_char
    return new


if __name__ == "__main__":
    result = unescape("\\a\\b\\\\c")
    assert result == "ab\\c", result

    result = escape("abc", ["b"])
    assert result == "a\\bc", result

    result = [m[1].span() for m in next_match(
        ["[ab]*", "[bc]*"], "abcbc", no_overlap=False)]
    assert result == [(0, 2), (1, 5), (3, 4)], result
    result = [m[1].span() for m in next_match(
        ["[ab]*", "[bc]*"], "abcbc", no_overlap=True)]
    assert result == [(0, 2), (3, 4)], result

    result = [m[1].span() for m in last_match(
        ["[ab]*", "[bc]*"], "abcbc", no_overlap=False)]
    assert result == [(1, 5), (3, 4), (0, 2)], result
    result = [m[1].span() for m in last_match(
        ["[ab]*", "[bc]*"], "abcbc", no_overlap=True)]
    assert result == [(1, 5)], result

    result = find_pairs("abcdefghi")
    assert result == [], result
    s = "csdf(asdf)bsdf"
    result = find_pairs(s)
    assert result == [Pair(s, (4, 5), (9, 10))], result
    s = "c(a[])"
    result = find_pairs(s)
    assert result == [
        Pair(s, (1, 2), (5, 6), [Pair(s, (3, 4), (4, 5))])], result
    s = "c(a[]{})"
    result = find_pairs(s)
    assert result == [
        Pair(s, (1, 2), (7, 8), [
            Pair(s, (3, 4), (4, 5)), Pair(s, (5, 6), (6, 7))
        ])
    ], result
    s = "123\"asdf\""
    result = find_pairs(s)
    assert result == [Pair(s, (3, 4), (8, 9))], result
    s = "123\"a{{f\""
    result = find_pairs(s)
    assert result == [Pair(s, (3, 4), (8, 9))], result
    s = "(\"a{{f\"absd) {()  [{}]}"
    result = find_pairs(s)
    assert result == [
        Pair(s, (0, 1), (11, 12), [
            Pair(s, (1, 2), (6, 7))
        ]),
        Pair(s, (13, 14), (22, 23), [
            Pair(s, (14, 15), (15, 16)),
            Pair(s, (18, 19), (21, 22), [
                Pair(s, (19, 20), (20, 21))
            ])
        ])
    ], result

    result = argument_split("asdf bsdf")
    assert result == ["asdf", "bsdf"], result
    result = argument_split("(asdf bsdf)")
    assert result == ["(asdf bsdf)"], result
    result = argument_split("\"as\\\"d{[(f\"")
    assert result == ["as\"d{[(f"], result
    result = argument_split("\"as\\\"d{[(f\" { a s \\d f }")
    assert result == ["as\"d{[(f", "{ a s d f }"], result
    result = argument_split(
        "/give @s minecraft:diamond_sword{display:{Name:'\"Super Slasher\"'}}")
    assert result == [
        "/give", "@s", "minecraft:diamond_sword{display:{Name:'\"Super Slasher\"'}}"], result
    result = argument_split("get 1-31 \"minecraft worlds 2\"")
    assert result == ["get", "1-31", "minecraft worlds 2"], result
