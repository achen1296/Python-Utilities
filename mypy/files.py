import os
import re
import shutil
import subprocess
import typing
from pathlib import Path


def create_file(path: os.PathLike, **kwargs):
    """ The last piece of the path is assumed to be a file, even if it doesn't have an extension (otherwise use makedirs). kwargs passed to open(), the result of which is returned. """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return open(path, "w", **kwargs)


def ignore_dot_dirs(dirpath: str, dirnames: list[str], filenames: list[str]) -> bool:
    """ For use with conditional_walk as a condition """
    return Path(dirpath).name[0] != "."


def conditional_walk(root: os.PathLike, condition: typing.Callable[[str, list[str], list[str]], bool]) -> tuple[str, list[str], list[str]]:
    for dirpath, dirnames, filenames in os.walk(root):
        # ignore folders not matching the condition
        if not condition(dirpath, dirnames, filenames):
            # skip all subdirs too
            dirnames[:] = []
            continue
        yield (dirpath, dirnames, filenames)


def __action_by_dict(planned_actions: dict[os.PathLike, os.PathLike], *, overwrite: bool, warn_if_exists: bool, action_callable: typing.Callable):
    for src in planned_actions:
        dst = planned_actions[src]
        if src != dst:
            p = Path(dst)
            if not overwrite and p.exists():
                if warn_if_exists:
                    print(f"Warn: {dst} exists, not overwiting with {src}")
            else:
                if warn_if_exists and p.exists():
                    print(
                        f"Warn: {dst} exists and is being overwritten with {src}")
                p.parent.mkdir(parents=True, exist_ok=True)
                action_callable(src, dst)


def move_by_dict(planned_moves: dict[os.PathLike, os.PathLike], *, overwrite=False, warn_if_exists=True) -> None:
    __action_by_dict(planned_moves, overwrite=overwrite,
                     warn_if_exists=warn_if_exists, action_callable=shutil.move)


def copy_by_dict(planned_copies: dict[os.PathLike, os.PathLike], *, overwrite=True, warn_if_exists=True) -> None:
    __action_by_dict(planned_copies, overwrite=overwrite,
                     warn_if_exists=warn_if_exists, action_callable=shutil.copy2)


def delete(file: os.PathLike):
    """Uses either os.remove or shutil.rmtree as appropriate."""
    path = Path(file)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        os.remove(path)


class FileMismatchException(Exception):
    pass


def mirror(src: os.PathLike, dst: os.PathLike, *, output: bool = False) -> None:
    src = Path(src)
    dst = Path(dst)
    if src.exists() and dst.exists() and src.is_dir() ^ dst.is_dir():
        raise FileMismatchException(
            f"One of {src} and {dst} is a file, the other a directory")
    if not src.is_dir():
        # copy file if newer
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            # src is newer than dst
            if output:
                print(f"Mirroring file {src} -> {dst}")
            shutil.copy2(src, dst)
    else:
        #src is dir
        if dst.exists():
            # delete files in dst that do not exist in src
            src_filenames = [f.name for f in src.iterdir()]
            to_delete = [f for f in dst.iterdir(
            ) if f.name not in src_filenames]
            for f in to_delete:
                if output:
                    print(f"Deleting {f}")
                delete(f)
        else:
            dst.mkdir()
        # recursively update files remaining
        for f in src.iterdir():
            mirror(f, dst.joinpath(f.name), output=output)


def mirror_by_dict(mirror_dict: dict[os.PathLike, typing.Union[os.PathLike, typing.Iterable[os.PathLike]]], *, output=False):
    for src in mirror_dict:
        destinations = mirror_dict[src]
        if isinstance(destinations, typing.Iterable):
            for dst in destinations:
                mirror(src, dst, output=output)
        else:
            mirror(src, destinations, output=output)


def zip(zip_path: os.PathLike, files: typing.Iterable[os.PathLike], *, overwrite: bool = False):
    """Zip a set of files using 7-zip"""
    zip_path = Path(zip_path)
    if len(zip_path.name) < 4 or zip_path.name[-4:] != ".zip":
        zip_path = zip_path.parent.joinpath(zip_path.name+".zip")
    if zip_path.exists():
        if overwrite:
            os.remove(zip_path)
        else:
            raise FileExistsError
    subprocess.run([f"{os.environ['HOMEPATH']}\\Programs\\7-zip\\7z.exe",
                    "a", "-tzip", str(zip_path)]+[str(f) for f in files])


def unzip(zip_path: os.PathLike, files: typing.Iterable[os.PathLike] = [
],  output_dir: os.PathLike = None, *, overwrite: bool = False):
    zip_path = Path(zip_path)
    if len(zip_path.name) < 4 or zip_path.name[-4:] != ".zip":
        zip_path = zip_path.parent.joinpath(zip_path.name+".zip")
    if output_dir == None:
        # controls unzip destination
        output_dir = zip_path.parent
    subprocess.run([f"{os.environ['HOMEPATH']}\\Programs\\7-zip\\7z.exe",
                    "x", "-tzip"]+(["-y"] if overwrite else [])+[f"-o{output_dir}", str(zip_path)]+[str(f) for f in files])


def long_names(root: os.PathLike) -> set[str]:
    long_set = set()
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            full = dirpath+os.sep+f
            if len(full) >= 260:
                long_set.add(full)
    return long_set


def re_split(file: os.PathLike, separator: str = "\s*\n\s*", *, exclude_empty: bool = True, **kwargs):
    """Like re.split() but does not load the whole file as a string all at once."""
    unprocessed = ""
    with open(file, **kwargs) as f:
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
