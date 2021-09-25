import os
import re
import typing
from typing import Iterable, Union

from mypy import files


def read_iterable_dict(list_dict: Iterable[str], *, key_value_separator: str = "\s*>\s*", value_list_separator: str = "\s*\|\s*",  comment: str = "\s*#", all_lists: bool = False) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a list of string entries.

    By default each is interpreted as key>value or key>val1|val2|... 
    If the k/v separator is not present, the value is automatically filled in with "" (or [] for all_lists=True), and if present multiple times in an entry, those after the first are interpreted as value text.

    ">" is the default key/value separator and "|" is the default value list separator so that file paths can be keys/values. The default comment starter is "#". Use "" for no comments or no value list separator. All string parameters are used as regular expressions.

    Entries that are one element long are not turned into lists by default. """
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


def read_string_dict(string_dict: str, *, entry_separator="\s*\n\s*", **kwargs) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a string, splitting on entry_separator and then using read_iterable_dict (passing kwargs). All string parameters except the string to read are used as regular expressions. """
    return read_iterable_dict(re.split(entry_separator, string_dict), **kwargs)


def read_file_dict(filename: os.PathLike, *, encoding=None, entry_separator="\s*\n\s*", **kwargs) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a file (using the specified encoding), converting it to a string and using read_iterable_dict (passing kwargs). All string parameters except filename and encoding are used as regular expressions. """
    if filename == None:
        return {}
    return read_iterable_dict(files.re_split(filename, entry_separator, encoding=encoding), **kwargs)


def write_iterable_dict(dictionary: dict[typing.Any, Union[typing.Any, Iterable[typing.Any]]], *, key_value_separator: str = ">", value_list_separator: str = "|") -> list[str]:
    """ Default separators > and |, same as reading dictionaries. 

    Keys and values can be of any type and are converted to strings using str(). For iterable values, they are converted one at a time with the separator inserted. 

    Keys with None or empty string values do not get the k/v separator. """
    l = []
    for key in sorted(dictionary):
        val = dictionary[key]
        try:
            if val == None or len(val) == 0:
                l.append(str(key))
                continue
        except TypeError:
            # no length
            pass
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


def write_string_dict(dictionary: dict[typing.Any, Union[typing.Any, Iterable[typing.Any]]], *, entry_separator: str = "\n", **kwargs) -> str:
    """ Joins the results of write_iterable_dict (passing kwargs) with the specified entry separator. """
    return entry_separator.join(write_iterable_dict(dictionary, **kwargs))


def write_file_dict(filename: os.PathLike, dictionary: dict[typing.Any, Union[typing.Any, Iterable[typing.Any]]], **kwargs) -> None:
    """ Writes the result of write_string_dict to a file. """
    with open(filename, "w", encoding="utf-8") as f:
        f.write(write_string_dict(dictionary, **kwargs))


def flip_dict(d: dict) -> dict:
    """ Produces a new dictionary where each original key becomes the value of its value (if just one value) or each of its original values (an iterable non-string value). """
    new_d = {}
    for key, val in d.items():
        if isinstance(val, Iterable) and not isinstance(val, str):
            for v in val:
                new_d[v] = key
        else:
            new_d[val] = key
    return new_d
