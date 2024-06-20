import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Sized

import files


def read_iterable_dict(iterable_dict: Iterable[str], *, key_value_separator: str = "\\s*>\\s*", value_list_separator: str = "\\s*\\|\\s*", comment: str = "\\s*#", all_lists: bool = False, key_transform: Callable[[Any], Any] | None = None, value_transform: Callable[[Any], Any] | None = None) -> dict:
    """ Reads a dictionary from a list of string entries.

    By default each is interpreted as key>value or key>val1|val2|...

    If the k/v separator is not present, the value is automatically filled in with "" (or [] for all_lists=True), and if present multiple times in an entry, those after the first are interpreted as value text.

    ">" is the default key/value separator and "|" is the default value list separator so that file paths can be keys/values, since these characters are not allowed in filenames.

    The default comment starter is "#". Use None for no comments or no value list separator. It must be at the start of a line, otherwise it is interpreted as key/value text.

    All string parameters are used as regular expressions.

    Entries that are one element long are not turned into lists by default.

    Undefined behavior for duplicate keys. """
    d = {}
    for entry in iterable_dict:
        # skip whitespace and comments
        if entry.strip() == "" or (comment is not None and re.match(comment, entry) != None):
            continue
        if re.search(key_value_separator, entry) is None:
            k = entry
            v = ""
        else:
            # only use first k-v separator (after that regarded as part of value)
            k, v = re.split(key_value_separator, entry, 1)
            if value_list_separator is not None and re.search(value_list_separator, v) != None:
                v = re.split(value_list_separator, v)
            elif all_lists:
                v = [v]
        if key_transform:
            k = key_transform(k)
        if value_transform:
            v = value_transform(v)
        d[k] = v
    return d


def read_string_dict(string_dict: str, *, entry_separator="\\s*\n\\s*", **kwargs) -> dict[str, str | list[str]]:
    """ Reads a dictionary from a string, splitting on entry_separator and then using read_iterable_dict (passing kwargs). All string parameters except the string to read are used as regular expressions. """
    return read_iterable_dict(re.split(entry_separator, string_dict), **kwargs)


def read_file_dict(filename: files.PathLike, *, encoding="utf8", entry_separator="\\s*\n\\s*", empty_on_not_exist: bool = False, **kwargs) -> dict[str, str | list[str]]:
    """ Reads a dictionary from a file (using the specified encoding), converting it to a string and using read_iterable_dict (passing kwargs). All string parameters except filename and encoding are used as regular expressions. """
    return read_iterable_dict(files.re_split(filename, entry_separator, encoding=encoding, empty_on_not_exist=empty_on_not_exist), **kwargs)


def write_iterable_dict(dictionary: dict[Any, Any | Iterable[Any]], *, key_value_separator: str = ">", value_list_separator: str = "|", sort_keys: Callable = str, sort_value_lists: Callable | None = None) -> list[str]:
    """ Default separators > and |, same as reading dictionaries.

    Keys and values can be of any type and are converted to strings using str(). For iterable values (but not strings), they are converted one at a time with the value list separator inserted.

    Keys with None, empty string, or empty iterable values do not get the k/v separator.

    Keys and iterable values are sorted using the keys given by sort_key and sort_value_lists respectively. """
    l = []
    if sort_keys:
        keys = sorted(dictionary, key=sort_keys)
    else:
        keys = dictionary
    for key in keys:
        val = dictionary[key]
        if val == None or (isinstance(val, Sized) and len(val) == 0):
            l.append(str(key))
            continue
        string = f"{key}{key_value_separator}"
        if isinstance(val, Iterable) and not isinstance(val, str):
            if sort_value_lists:
                val = sorted(val, key=sort_value_lists)
            string += value_list_separator.join((str(v) for v in val))
        else:
            string += str(val)
        l.append(string)
    return l


def write_string_dict(dictionary: dict[Any, Any | Iterable[Any]], *, entry_separator: str = "\n", **kwargs) -> str:
    """ Joins the results of write_iterable_dict (passing kwargs) with the specified entry separator. """
    return entry_separator.join(write_iterable_dict(dictionary, **kwargs))


def write_file_dict(filename: files.PathLike, dictionary: dict[Any, Any | Iterable[Any]], encoding="utf8", **kwargs) -> None:
    """ Writes the result of write_string_dict to a file. """
    with open(filename, "w", encoding=encoding) as f:
        f.write(write_string_dict(dictionary, **kwargs))


def _dict_list_add(d: dict, key, value):
    """ If the key already has a value in the dictionary d, and that value is not a list, then the new combined value is a list containing the original value, then the new value. If the original value is already a list (but not any other kind of Iterable), the new value is appended. """
    if key in d:
        original_value = d[key]
        if isinstance(original_value, list):
            original_value.append(value)
        else:
            d[key] = [original_value, value]
    else:
        d[key] = value


def flip_dict(d: dict) -> dict:
    """ Produces a new dictionary where each original key becomes the value, with the original value (if just one value) or each of its original values (an iterable non-string value) as the key. If a duplicate value (that becomes a key) is found, then the keys (that become values) are combined into a list as the new value.  """
    new_d = {}
    for key, value in d.items():
        if isinstance(value, Iterable) and not isinstance(value, str):
            for v in value:
                _dict_list_add(new_d, v, key)
        else:
            _dict_list_add(new_d, value, key)
    return new_d


class FileBackedDict(dict):
    def __init__(self, file: files.PathLike, *read_args, **read_kwargs):
        """ Call batch() to delay updates to file, then call flush(). """
        self.file = Path(file)
        if self.file.exists():
            self.update(read_file_dict(
                self.file, *read_args, **read_kwargs))

        self.batch_flag = False

        self.write_args = ()
        self.write_kwargs = {}

    def set_write_args(self, *write_args, **write_kwargs):
        self.write_args = write_args
        self.write_kwargs = write_kwargs

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if not self.batch_flag:
            self.flush()

    def batch(self):
        self.batch_flag = True

    def flush(self):
        self.batch_flag = False
        write_file_dict(self.file, self, *self.write_args,
                        **self.write_kwargs)
