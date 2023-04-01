""" This module is for setting permanent environment variables. For temporary environment variables, os.environ can be used. """

import os
import platform
import subprocess

# stores environment variables set recently, since they will otherwise not be registered until the program is restarted
_cache = {}

if platform.system() != "Windows":
    raise NotImplementedError


def set(name: str, value: str):
    name = name.replace("\"", "")
    value = value.replace("\"", "")
    _cache[name] = value
    subprocess.run(f"setx \"{name}\" \"{value}\"", shell=True,
                   creationflags=subprocess.CREATE_NO_WINDOW)


def get(name: str):
    try:
        return _cache[name]
    except KeyError:
        return os.environ[name]


def list_append(name: str, value: str):
    lst = get(name).split(";")
    lst.append(value)
    set(name, ";".join(lst))
