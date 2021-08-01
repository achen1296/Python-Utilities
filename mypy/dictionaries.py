from typing import Union, Iterable
import re


def read_iterable_dict(list_dict: Iterable[str], *, key_value_sep: str = ">", value_list_sep: str = "\|",  comment: str = "\s*#", all_lists: bool = False) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a list of string entries, by default each is interpreted as key>value or key>val1|val2|... """
    d = {}
    for entry in list_dict:
        # skip whitespace and comments
        if entry.strip() == "" or (comment != None and re.match(comment, entry) != None):
            continue
        if re.search(key_value_sep, entry) == None:
            # no k-v separator, empty value
            if all_lists:
                d[entry] = []
            else:
                d[entry] = ""
        else:
            # only use first k-v separator (after that regarded as part of value)
            k, v = re.split(key_value_sep, entry, 1)
            if re.search(value_list_sep, v) != None:
                v = re.split(value_list_sep, v)
            elif all_lists:
                v = [v]
            d[k] = v
    return d


def read_string_dict(string_dict: str, *, entry_terminator="\n", key_value_sep: str = "\s*>\s*", value_list_sep: str = "\s*\|\s*",  comment: str = "\s*#", all_lists: bool = False) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a string, splitting on entry_terminator and then using read_iterable_dict """
    l = locals()
    del l["string_dict"]
    del l["entry_terminator"]
    return read_iterable_dict(re.split(entry_terminator, string_dict), **l)


def read_file_dict(file_name: str, *, encoding=None, entry_terminator="\n", key_value_sep: str = ">", value_list_sep: str = "\|",  comment: str = "\s*#", all_lists: bool = False) -> dict[str, Union[str, list[str]]]:
    """ Reads a dictionary from a file, converting it to a string and using read_string_dict """
    l = locals()
    del l["file_name"]
    del l["encoding"]

    if file_name == None:
        return {}

    with open(file_name, encoding=encoding) as file:
        file_string = ""
        line = ""
        try:
            for line in file:
                file_string += line
        except UnicodeDecodeError:
            print("error in \"" + line + "\"")
            raise

    return read_string_dict(file_string, **l)


def write_iterable_dict(dictionary: dict[str, Union[str, Iterable[str]]], *, key_value_sep: str = ">", value_list_sep: str = "|") -> list[str]:
    l = []
    for key in sorted(dictionary):
        val = dictionary[key]
        if val == None or len(val) == 0:
            l.append(key)
            continue
        string = f"{key}{key_value_sep}"
        if isinstance(val, Iterable) and not isinstance(val, str):
            first = True
            for v in sorted(val):
                if first:
                    first = False
                else:
                    string += value_list_sep
                string += str(v)
        else:
            string += str(val)
        l.append(string)
    return l


def write_string_dict(dictionary: dict[str, Union[str, Iterable[str]]], *, entry_terminator: str = "\n", **kwargs) -> str:
    string = ""
    list_dict = write_iterable_dict(dictionary, **kwargs)
    for entry in list_dict:
        string += entry+entry_terminator
    return string


def write_file_dict(file_name: str, dictionary: dict[str, Union[str, list[str]]], **kwargs) -> None:
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(write_string_dict(dictionary))


def flip_dict(d: dict) -> dict:
    new_d = {}
    for key, val in d.items():
        if isinstance(val, list) or isinstance(val, set) or isinstance(val, tuple):
            for v in val:
                new_d[v] = key
        else:
            new_d[val] = key
    return new_d
