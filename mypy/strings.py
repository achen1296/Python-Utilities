import re
import typing


def unescape(s: str, *, escape_char: str = "\\") -> str:
    # removes one level of escape \s
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
            s = s[:i]+"\\"+s[i:]
            i += 1
        i += 1
    return s


def __argument_split_finish(s: str, tokens: list[str], start: int, remove_outer: dict[str, str], remove_empty_tokens: bool, unescape_bool: bool):
    # last token
    tokens.append(s[start:])
    if remove_outer != None:
        new_tokens = []
        for t in tokens:
            for start in remove_outer:
                match = re.match(f"{start}(.*?){remove_outer[start]}$", t)
                if match != None:
                    t = match.group(1)
            new_tokens.append(t)
        tokens = new_tokens
    if remove_empty_tokens:
        tokens = [t for t in tokens if t != ""]
    if unescape_bool:
        tokens = [unescape(t) for t in tokens]
    return tokens


def argument_split(s: str, *, sep: str = "\s+", compound_pairs: dict[str, str] = None, ignore_internal_pairs: typing.Iterable[str] = None, remove_outer: dict[str, str] = {"\"": "\"", "'": "'"}, remove_empty_tokens=True, unescape=True) -> list[str]:
    """ Like str's regular split method, but accounts for arguments that contain the split separator if they occur in compounds (for example, perhaps spaces in quoted strings should not result in a split). Arguments for compound_pairs and ignore_internal_pairs are passed to find_pair. """
    sep_comp = re.compile(sep)
    tokens = []
    start = 0
    while True:
        next_sep = sep_comp.search(s, start)
        if next_sep == None:
            return __argument_split_finish(s, tokens, start,  remove_outer, remove_empty_tokens, unescape)
        # end just before next sep
        end = next_sep.start()
        # skip over compounds
        i = start
        while i < end:
            try:
                i = find_pairs(s, i, pairs=compound_pairs,
                               ignore_internal_pairs=ignore_internal_pairs) + 1
                # find next sep after compound
                next_sep = sep_comp.search(s, i)
                if next_sep == None:
                    return __argument_split_finish(s, tokens, start, remove_outer, remove_empty_tokens, unescape)
                # end just before next sep
                end = next_sep.start()
            except NoPairException:
                i += 1
        # reached a separator without finding another compound first
        tokens.append(s[start:end])
        # start after the next sep
        start = next_sep.end()


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
    def __init__(self, original_str: str, start_str: str, end_str: str, start_index: int, end_index: int, internal_pairs: list[Pair] = []):
        self.original_str = original_str
        self.start_str = start_str
        self.end_str = end_str
        self.start_index = start_index
        self.end_index = end_index
        self.internal_pairs = internal_pairs

    def add_internal(self, internal: Pair):
        self.internal_pairs.append(internal)


def find_pairs(s: str, *, pairs: dict[str, str] = None, ignore_internal_pairs: typing.Iterable[str] = None) -> list[tuple[int, int]]:
    """ Finds pairs in the string of the specified expressions and returns the indices of the start and end of each pair (the first index of the matches).

    Any unbalanced pairs result in a NoPairException. The expressions for pair starts and ends should not allow overlap with themselves (although pair starts and ends can be the same character, like quotes), otherwise the results are undefined.

    For example, `find_pairs("[ex(am)\\"{\\"p\\\\]le]")`:

    First, the [ is found. Then ( is found, before matching immediately with ). Then the quote is found. Since it is inside quotes, the { is ignored. The next matching quote is found. The next escaped \] is ignored, and finally the first [ is paired. Thus the complete return value is `[(0,15),(7,9),(3,6)]` -- in reverse order of the pair end index.

    If the `pairs` and `ignore_internal_pairs` parameters are left as None, unescaped {, [, (, ", and ' characters are matched with their opposites. However, `pairs` can be specified as a dictionary, with the regular expression for a pair start mapping to the regular expression for the corresponding paired character. The ignoring of escaped characters (those preceded by an \\ character) is part of the default regular expressions for `pairs`. `ignore_internal_pairs` is a set of pair starter regular expressions and is only used if `pairs` matches a piece of the string first. """

    # negative look behind for \
    NO_ESCAPE = "(?<!\\\\)"

    if pairs == None:
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
        while next_start != None and next_end != None and next_start[1].end() <= next_end[1].start():
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
            if next_start[1].span() == next_end[1].span():
                continue
            raise NoPairException(
                f"Ran out of pair starts to match with {next_end[1]}. {pair_list} {start_stack}")
        if pairs[popped_start[0]] != next_end[0]:
            # pair match failed; attempt to interpret next end as a start instead (e.g. quotes by default)
            if next_start[1].span() == next_end[1].span():
                # return popped pair start to stack
                start_stack.append(popped_start)
                continue
            # not also a start
            raise NoPairException(
                f"Pair starting {popped_start[1]} did not match with a {pairs[popped_start[0]]}, {next_end[1]} found instead. {pair_list} {start_stack}")
        # pair matched
        pair_list = [(popped_start[1].start(),
                      next_end[1].start())] + pair_list
        ignoring_internal = False
        # if end was also counted as a start, skip it
        if next_start != None and next_start[1].span() == next_end[1].span():
            next_start = next(pair_starts_gen, None)
    # did not also exhaust all pair starts
    if next_start != None:
        raise NoPairException(
            f"Pair starting {next_start[1]} did not match with a {pairs[next_start[0]]}, ran out of pair ends instead. {pair_list} {start_stack}")
    return pair_list


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
    result = find_pairs("csdf(asdf)bsdf")
    assert result == [(4, 9)], result
    result = find_pairs("c(a[])")
    assert result == [(1, 5), (3, 4)], result
    result = find_pairs("c(a[]{})")
    assert result == [(1, 7), (5, 6), (3, 4)], result
    result = find_pairs("123\"asdf\"")
    assert result == [(3, 8)], result
    result = find_pairs("123\"a{{f\"")
    assert result == [(3, 8)], result
    result = find_pairs("(\"a{{f\"absd) {()  []}")
    assert result == [(13, 20), (18, 19), (14, 15), (0, 11), (1, 6)], result
