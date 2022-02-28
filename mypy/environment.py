import os
import subprocess

# stores environment variables set recently, since they will otherwise not be registered until the program is restarted
_cache = {}


def set(name: str, value: str):
    _cache[name] = value
    subprocess.run(f"setx \"{name}\" \"{value}\"", shell=True)


def get(name: str):
    try:
        return _cache[name]
    except KeyError:
        return os.environ[name]


def list_append(name: str, value: str):
    lst = get(name).split(";")
    lst.append(value)
    set(name, ";".join(lst))
