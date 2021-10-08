import re
import typing


def unescape(s: str, *, escape_char="\\") -> str:
    # removes one level of escape \s
    i = 0
    while i < len(s):
        if s[i] == escape_char:
            s = s[:i] + s[i+1:]
        # if there was an escape \, this skips over the character after it, in case it is an escaped \ i.e. \\, so only the first one is removed
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


def next_match(regular_expressions: typing.Iterable[str], s: str, *, flags=0):
    """ Generates tuples containing the regular expression that next matches earliest in the string (if start indicies tie, earliest end is first) and the match object it produces. """
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
        first_start = len(s)+1
        first_end = len(s)+1
        next_start = len(s)+1
        next_end = len(s)+1
        # find earliest match
        for r, match in matches.items():
            m_start, m_end = match.span()
            if m_start < first_start or (m_start == first_start and m_end < first_end):
                first_start = m_start
                first_end = m_end
                first_r = r
                first_match = match
            if m_start < next_start or (m_start == next_start and m_end < next_end):
                next_start = m_start
                next_end = m_end
                next_r = r
                next_match = match
        try:
            matches[first_r] = next(iters[first_r])
            matches[next_r] = next(iters[next_r])
        except StopIteration:
            del matches[first_r]
            del iters[first_r]
        # skip empty matches
        if first_start < first_end:
            yield (first_r, first_match)
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


class NoPairException(Exception):
    pass


def find_pairs(s: str, start: int = 0, *, pairs: dict[str, str] = None, ignore_internal_pairs=None) -> list[tuple[int, int]]:
    """ Finds pairs in the string of the specified characters and returns start/end indices.

    Raises NoPairException if a pair is not found.

    For example, `find_pairs("[ex(am)\\"{\\"p\\\\]le]")`:

    First, the [ is found. Then ( is found, before matching immediately with ). Then the quote is found. Since it is inside quotes, the { is ignored. The next matching quote is found. The next escaped \] is ignored, and finally the first [ is paired. Thus the complete return value is `[(0,15),(8,9),(3,6)]`, with the pairs noted down in the opposite order they are completed. 

    If the `pairs` and `ignore_internal_pairs` parameters are left as None, this is the behavior. However, `pairs` can be specified as a dictionary, with the regular expression for a pair start mapping to the regular expression for the corresponding paired character. The ignoring of escaped characters is part of the default regular expressions for `pairs`. `ignore_internal_pairs` is a set of pair starter regular expressions and is only used if `pairs` matches a piece of the string first. 

    Any unbalanced pairs result in a NoPairException. """

    # negative look behind for \
    NO_ESCAPE = "(?<!\\\\)"

    if pairs == None:
        pairs = {NO_ESCAPE+"\"": NO_ESCAPE+"\"", NO_ESCAPE+"'": NO_ESCAPE+"'", NO_ESCAPE+"\(": NO_ESCAPE+"\)",
                 NO_ESCAPE+"\[": NO_ESCAPE+"\]", NO_ESCAPE+"{": NO_ESCAPE+"}"}
    if ignore_internal_pairs == None:
        ignore_internal_pairs = {"\"", "\'"}

    start_str = None
    for re_str in pairs:
        re_comp = re.compile(re_str)
        match = re_comp.match(s, start)
        if match != None:
            start_str = s[match.start():match.end()]
            start_re = re_str
            break
    if start_str == None:
        raise NoPairException(
            f"No pair start at index {start} found in <{s}>")
    end_re = re.compile(pairs[start_re])

    ignore_internal = False
    for re_str in ignore_internal_pairs:
        if re.match(re_str, start_str) != None:
            ignore_internal = True
            break

    i = start+1
    length = len(s)
    while i < length:
        end_re = re.compile(end_re)
        if end_re.match(s, i):
            # print(f"{start}-{i}")
            return i
        if ignore_internal:
            # simply continue if internal pairs are not being considered
            i += 1
        else:
            # skip internal pairs
            try:
                i = find_pairs(s, i, pairs=pairs)+1
                continue
            except NoPairException:
                i += 1

    raise ValueError(
        f"Pair not found for {start_str} at index {start} in <{s}>")


if __name__ == "__main__":
    assert argument_split("\"{asd[ pow ]f pootis}\" ([]   A ) {pow} \{\{\{ \"asdf\"\n") == [
        "{asd[ pow ]f pootis}", "([]   A )", "{pow}", "{{{", "asdf"]
    result = find_pairs("[ex(am)\"{\"p\\]le]")
    assert result == [(0, 15), (8, 9), (3, 6)], result
    assert argument_split(
        "type=minecraft:area_effect_cloud,tag=marker,limit=1,name=\\\"<marker name>\\\"", sep=",") == ["type=minecraft:area_effect_cloud", "tag=marker", "limit=1", "name=\"<marker name>\""]
    assert unescape("\'a\\\\sdf\'") == "\'a\\sdf\'"
