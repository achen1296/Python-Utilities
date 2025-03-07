# Functions for reading files and their metadata

import hashlib
import itertools
import re
from typing import Iterable

from .consts import *
from .walk import *


def long_names(root: PathLike = ".", **kwargs) -> Iterable[Path]:
    """ Returns a set of files whose absolute paths are >= 260 characters, which means they are too long for some Windows applications. Not > 260 because, as the page linked below describes, Windows includes the NUL character at the end in the count, while Python strings do not.

    docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation """
    def file_action(f: Path, d: int):
        if len(str(f)) >= 260:
            yield f

    prune_walk_kwargs(kwargs)
    return walk(Path(root).resolve(), file_action=file_action, **kwargs)


def id(file: PathLike):
    return os.stat(file).st_ino


BYTE = 1
KB = KILOBYTE = 1E3
MB = MEGABYTE = 1E6
GB = GIGABYTE = 1E9
TB = TERABYTE = 1E12


def size(root: PathLike = ".", unit: float = BYTE, follow_symlinks: bool = False):
    """File size in bytes, using os.stat. If path is a folder, sums up the size of all files contained in it recursively. The result is divided by the argument to unit. For convenience, constants for bytes, KB, MB, GB, and TB have been specified. """
    def size_recursive(path: Path):
        if path.is_symlink():
            if follow_symlinks:
                target = path.readlink()
                if target.is_absolute():
                    return size_recursive(target)
                else:
                    return size_recursive(path.parent.joinpath(target))
            else:
                try:
                    return os.stat(path).st_size
                except:
                    # e.g. FileNotFoundError for a broken symbolic link
                    return 0
        elif path.is_file():
            try:
                return os.stat(path).st_size
            except:
                return 0
        else:
            return sum(
                (size_recursive(f) for f in path.iterdir())
            )
    return size_recursive(Path(root))/unit


# base 10, following SI units: kilo, mega, giga, tera, peta, exa, zetta, yotta, ronna, quetta
SIZE_UNITS_10 = [" bytes", "KB", "MB", "GB",
                 "TB", "PB", "EB", "ZB", "YB", "RB", "QB"]
# base-2 versions: kibi, mebi, gibi, tebi, pebi, exbi, zebi, yobi, robi, quebi
SIZE_UNITS_2 = [" bytes", "KiB", "MiB", "GiB",
                "TiB", "PiB", "EiB", "ZiB", "YiB", "RiB", "QiB"]


def format_size(size_bytes: int | float, base_2=False):
    if base_2:
        divisor = 1024
    else:
        divisor = 1000
    u = 0
    while size_bytes > divisor:
        size_bytes /= divisor
        u += 1
    if base_2:
        return f"{size_bytes:.3f} {SIZE_UNITS_2[u]}"
    else:
        return f"{size_bytes:.3f} {SIZE_UNITS_10[u]}"


def count(root: PathLike = "."):
    """Counts files recursively. Does not follow symlinks, they are counted as one file instead."""
    def count_recursive(path: Path):
        if path.is_symlink() or path.is_file():
            return 1
        else:
            return sum(
                (count_recursive(f) for f in path.iterdir())
            )
    return count_recursive(Path(root))


def hash(file: PathLike, *, hash_function: str = "MD5", size: int = -1, hex: bool = True) -> str | bytes:
    """ Hash with the specified function (default MD5). """
    with open(file, "rb") as f:
        h = hashlib.new(hash_function, f.read(size), usedforsecurity=False)
        return h.hexdigest() if hex else h.digest()


def is_empty(root: PathLike = ".") -> bool:
    """ Considers a directory empty if all of its subdirectories are empty. Always returns False for a file. """
    def is_empty_recursive(root: Path):
        if root.is_file():
            return False
        for f in root.iterdir():
            if not is_empty_recursive(f):
                return False
        return True

    root = Path(root)
    return is_empty_recursive(root)


def list_files(root: PathLike = ".", *, skip_file: Callable[[PathLike, int], bool] | None = None, skip_dir: Callable[[PathLike, int], bool] | None = None, **kwargs) -> Iterable[Path]:

    def file_action(p: Path, i: int):
        if skip_file is None or not skip_file(p, i):
            yield p

    prune_walk_kwargs(kwargs)
    return walk(root, file_action=file_action, skip_dir=skip_dir, **kwargs)


def re_split(file: PathLike, separator: str = "\\s*\n\\s*", *, exclude_empty: bool = True, encoding="utf8", empty_on_not_exist: bool = False, ** open_kwargs):
    """Like re.split() but does not load the whole file as a string all at once."""
    if not Path(file).exists() and empty_on_not_exist:
        return
    unprocessed = ""
    with open(file, encoding=encoding, **open_kwargs) as f:
        for line in f:
            unprocessed += line
            seps = list(re.finditer(separator, unprocessed))
            # no separators found yet
            if len(seps) == 0:
                continue
            # read lines until either the last separator does not reach the end of the string or, if there is a separator reaching the end of the string, there are at least two separators, in which case the second-last one is used as the split instead of the last one, so that the regular expression is allowed to be as greedy as possible
            last = seps[-1]
            if last.end() == len(unprocessed):
                if len(seps) < 2:
                    continue
                else:
                    last = seps[-2]
            # use the normal re.split function in case the line introduced more than one additional separator
            for s in re.split(separator, unprocessed[:last.start()]):
                if exclude_empty and s == "":
                    continue
                yield s
            unprocessed = unprocessed[last.end():]
        # yield what is left after the whole file is read
        for s in re.split(separator, unprocessed):
            if exclude_empty and s == "":
                continue
            yield s


def text_search(query: str, root: PathLike = ".", output_errors=False, pre_context: int = 2, post_context: int = 2, **kwargs) -> Iterable[tuple[Path, tuple[int, int], list[str]]]:
    """ Search for text in files. Intended to be used on the command line, and will not find text that spans in between lines. Yields additional lines around the one with the query text specified as pre_context and post_context. """
    def file_action(p: Path, i: int):
        context: list[str] = []
        context_length = pre_context + post_context + 1
        delayed_yield: list[int] = []
        line_num = 1
        with open(p, encoding="utf8") as f:
            for line in f:
                context.append(line)
                if len(context) > context_length:
                    context.pop(0)
                if query.lower() in line.lower():
                    delayed_yield.append(post_context+1)
                for i in range(0, len(delayed_yield)):
                    delayed_yield[i] -= 1
                if len(delayed_yield) > 0 and delayed_yield[0] <= 0:
                    # make a copy of the context to yield, otherwise always produces the last few lines
                    yield p, (max(line_num - context_length+1, 1), line_num), [l for l in context]
                    delayed_yield.pop(0)
                line_num += 1
        line_num -= 1
        if len(delayed_yield) > 0:
            yield p, (max(line_num - context_length+1, 1), line_num), context

    def error_action(p: Path, i: int, e: Exception):
        if output_errors:
            print("error on " + str(p))
            print(e)

    prune_walk_kwargs(kwargs)
    return walk(root, file_action=file_action, error_action=error_action, **kwargs)


def search(name_query: str, root: PathLike = ".", output_errors=False, **kwargs) -> Iterable[Path]:
    def name(p: Path, i: int):
        if name_query.lower() in p.name.lower():
            yield p

    def error_action(p: Path, i: int, e: Exception):
        if output_errors:
            print("error on " + str(p))

    prune_walk_kwargs(kwargs)
    return walk(root, file_action=name, dir_action=name, error_action=error_action, **kwargs)


def find_ascii(file: PathLike, length_threshold: int) -> Iterable[tuple[int, bytearray]]:
    """ Returns runs of bytes representing printable ASCII characters (32-126) at least as long as the length threshold, along with their indices in the file. """
    def is_ascii(b: bytes):
        return all((32 <= i <= 126 for i in b))

    with open(file, "rb") as f:
        ascii_streak = bytearray()
        bytes_read = 0
        while True:
            b = f.read(1)
            if len(b) == 0:
                # EOF
                break
            if is_ascii(b):
                ascii_streak += b
            else:
                if len(ascii_streak) >= length_threshold:
                    yield bytes_read, ascii_streak
                ascii_streak = bytearray()
            bytes_read += 1


def _last_common_ancestor_2(p1: Path | None, p2: Path | None):
    if p1 is None or p2 is None:
        return None
    for par in itertools.chain([p1], p1.parents):
        if par == p2 or par in p2.parents:
            return par
    return None


def last_common_ancestor(*ps: Path):
    if len(ps) == 0:
        return None
    lca = ps[0]
    for p in ps[1:]:
        lca = _last_common_ancestor_2(lca, p)
    return lca


if WINDOWS:
    import winreg

    def absolute_with_env(path: PathLike) -> Path:
        path: str = str(path)
        path = winreg.ExpandEnvironmentStrings(path)
        return Path(path).absolute()

    def resolve_with_env(path: PathLike) -> Path:
        path: str = str(path)
        path = winreg.ExpandEnvironmentStrings(path)
        return Path(path).resolve()

    def with_env(path: PathLike) -> Path:
        path: str = str(path)
        path = winreg.ExpandEnvironmentStrings(path)
        return Path(path)
