import re
import typing


def unescape(s: str) -> str:
    # removes one level of escape \s
    i = 0
    while i < len(s):
        if s[i] == "\\":
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
                i = find_pair(s, i, pairs=compound_pairs,
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


class NoPairException(Exception):
    pass


def find_pair(s: str, start: int = 0, *, pairs: dict[str, str] = None, ignore_internal_pairs=None) -> int:
    """ Finds the index of the pair of the specified character, considering internal pairs. 

    Raises NoPairException if a pair is not found.

    For example, find_pair("[ex(am)\"{\"p\\]le]", 0) should return the index of the last character. The () pair was considered, and the { inside the quotation marks was ignored as well as the escaped ]. If pairs is none, defaults to ", ', (, [, { with corresponding matches and all ignoring if escaped. ignore_internal_pairs defaults to just " and ' (also ignores if escaped, because a match is not attempted if the quote was not considered as pair start first) to avoid attempting to pair compound delimiters inside strings. """
    if pairs == None:
        pairs = {"(?<!\\\\)\"": "(?<!\\\\)\"", "(?<!\\\\)'": "(?<!\\\\)'", "(?<!\\\\)\(": "(?<!\\\\)\)",
                 "(?<!\\\\)\[": "(?<!\\\\)\]", "(?<!\\\\){": "(?<!\\\\)}"}
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
                i = find_pair(s, i, pairs=pairs)+1
                continue
            except NoPairException:
                i += 1

    raise ValueError(
        f"Pair not found for {start_str} at index {start} in <{s}>")


if __name__ == "__main__":
    assert argument_split("\"{asd[ pow ]f pootis}\" ([]   A ) {pow} \{\{\{ \"asdf\"\n") == [
        "{asd[ pow ]f pootis}", "([]   A )", "{pow}", "{{{", "asdf"]
    assert find_pair(
        "@a[nbt={Inventory:[{Slot:-106b, id:\"minecraft:iron_ingot\",tag:{display:{Name:'{\"text\":\"Item Magnet\"}'},Enchantments:[{lvl:10s,id:\"minecraft:looting\"},{lvl:10s,id:\"minecraft:lure\"}]}}]}]", 2) == 184
    assert argument_split(
        "type=minecraft:area_effect_cloud,tag=marker,limit=1,name=\\\"<marker name>\\\"", sep=",") == ["type=minecraft:area_effect_cloud", "tag=marker", "limit=1", "name=\"<marker name>\""]
    assert unescape("\'a\\\\sdf\'") == "\'a\\sdf\'"
