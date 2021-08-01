import subprocess
import os
import re
import shutil
import time
import typing
from pathlib import Path


def create_file(path: os.PathLike, **kwargs):
    """ The last piece of the path is assumed to be a file, even if it doesn't have an extension (otherwise use makedirs). kwargs passed to open(). """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return open(path, "w", **kwargs)


def ignore_dot_dirs(dirpath: str, dirnames: list[str], filenames: list[str]) -> bool:
    """ For use with conditional_walk as a condition """
    return os.basename(dirpath)[0] != "."


def conditional_walk(root: os.PathLike, condition: typing.Callable[[str, list[str], list[str]], bool]) -> tuple[str, list[str], list[str]]:
    for dirpath, dirnames, filenames in os.walk(root):
        # ignore folders not matching the condition
        if not condition(dirpath=dirpath, dirnames=dirnames, filenames=filenames):
            # skip all subdirs too
            dirnames[:] = []
            continue
        yield (dirpath, dirnames, filenames)


def move_by_dict(planned_moves: dict[os.PathLike, os.PathLike], *, overwrite=True, warn_if_exists=True) -> None:
    for src in planned_moves:
        dst = planned_moves[src]
        if src != dst:
            p = Path(dst)
            if not overwrite and p.exists():
                if warn_if_exists:
                    print(f"{dst} exists, not overwiting")
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(src, dst)


def copy_by_dict(planned_copies: dict[os.PathLike, os.PathLike], *, overwrite=True, warn_if_exists=True) -> None:
    for src in planned_copies:
        dst = planned_copies[src]
        if src != dst:
            p = Path(dst)
            if not overwrite and p.exists():
                if warn_if_exists:
                    print(f"{dst} exists, not overwiting")
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)


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
                print(f"Mirroring {src} -> {dst}")
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
                if f.is_dir():
                    shutil.rmtree(f)
                else:
                    os.remove(f)
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


def zip(zip_path: os.PathLike, files: typing.Iterable[os.PathLike], output_dir: os.PathLike = None, *, overwrite: bool = False):
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
