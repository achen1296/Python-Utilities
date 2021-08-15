from os import write
from typing import Union, Iterable
import re


def read_iterable_dict(list_dict: Iterable[str], *, key_value_separator: str = "\s*>\s*", value_list_separator: str = "\s*\|\s*",  comment: str = "\s*#", all_lists: bool = False) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a list of string entries, by default each is interpreted as key>value or key>val1|val2|... ">" is the default key/value separator and "|" is the default value list separator so that file paths can be keys/values. The default comment starter is "#" and entries that are one element long are not turned into lists by default. Use "" for no comments or no value list separator. All string parameters are used as regular expressions. """
    d = {}
    for entry in list_dict:
        # skip whitespace and comments
        if entry.strip() == "" or (comment != "" and re.match(comment, entry) != None):
            continue
        if re.search(key_value_separator, entry) == None:
            # no k-v separator, empty value
            if all_lists:
                d[entry] = []
            else:
                d[entry] = ""
        else:
            # only use first k-v separator (after that regarded as part of value)
            k, v = re.split(key_value_separator, entry, 1)
            if value_list_separator != "" and re.search(value_list_separator, v) != None:
                v = re.split(value_list_separator, v)
            elif all_lists:
                v = [v]
            d[k] = v
    return d


def read_string_dict(string_dict: str, *, entry_separator="\n", **kwargs) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a string, splitting on entry_separator and then using read_iterable_dict. All string parameters except the string to read are used as regular expressions. """
    return read_iterable_dict(re.split(entry_separator, string_dict), **kwargs)


def read_file_dict(filename: str, *, encoding=None, entry_separator="\n", **kwargs) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a file, converting it to a string and using read_string_dict. All string parameters except filename are used as regular expressions. """
    if filename == None:
        return {}
    d = {}
    with open(filename, encoding=encoding) as file:
        # used like a buffer
        unprocessed = ""
        for line in file:
            unprocessed += line
            try:
                last_terminator = unprocessed.rindex(entry_separator)
            except ValueError:
                # continue reading the file until an entry terminator is found
                pass
            else:
                # process up to the last terminator
                d.update(read_string_dict(
                    unprocessed[:last_terminator], entry_separator=entry_separator, **kwargs))
                unprocessed = unprocessed[last_terminator+1:]
        # last update after reading the whole file, in case it doesn't end with a final terminator
        d.update(read_string_dict(
            unprocessed, entry_separator=entry_separator, **kwargs))
    return d


def write_iterable_dict(dictionary: dict[str, Union[str, Iterable[str]]], *, key_value_separator: str = ">", value_list_separator: str = "|") -> list[str]:
    """Default separators > and |, same as reading dictionaries. """
    l = []
    for key in sorted(dictionary):
        val = dictionary[key]
        if val == None or len(val) == 0:
            l.append(key)
            continue
        string = f"{key}{key_value_separator}"
        if isinstance(val, Iterable) and not isinstance(val, str):
            first = True
            for v in sorted(val):
                if first:
                    first = False
                else:
                    string += value_list_separator
                string += str(v)
        else:
            string += str(val)
        l.append(string)
    return l


def write_string_dict(dictionary: dict[str, Union[str, Iterable[str]]], *, entry_separator: str = "\n", **kwargs) -> str:
    return entry_separator.join(write_iterable_dict(dictionary, **kwargs))


def write_file_dict(file_name: str, dictionary: dict[str, Union[str, list[str]]], **kwargs) -> None:
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(write_string_dict(dictionary, **kwargs))


def flip_dict(d: dict) -> dict:
    new_d = {}
    for key, val in d.items():
        if isinstance(val, Iterable):
            for v in val:
                new_d[v] = key
        else:
            new_d[val] = key
    return new_d
