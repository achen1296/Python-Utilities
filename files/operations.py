# (c) Andrew Chen (https://github.com/achen1296)

# Functions for writing files

import io
import re
import shutil
import subprocess
import time
import traceback
import zipfile
from pathlib import Path
from typing import Callable, Iterable
from zipfile import ZipFile

from more_itertools import consume

from .consts import *
from .stats import *
from .walk import *


def create_file(path: PathLike, binary=False, **open_kwargs):
    """ The last piece of the path is assumed to be a file, even if it doesn't have an extension (otherwise use `os.makedirs` / `path.mkdir(..., parents=True))`. open_kwargs passed to open(), the result of which is returned. """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        mode = "wb"
    else:
        mode = "w"
    return open(path, mode, **open_kwargs)


def copy(src: PathLike, dst: PathLike, *, output=False, **kwargs):
    shutil.copy2(src, dst, **kwargs)
    if output:
        print(f"Copied <{src}> -> <{dst}>")


def move(src: PathLike, dst: PathLike, *, output=False, **kwargs):
    shutil.move(src, dst, **kwargs)
    if output:
        print(f"Moved <{src}> -> <{dst}>")


def __file_action_by_dict(planned_actions: dict[PathLike, PathLike], action_callable: Callable[[PathLike, PathLike], None], action_past_tense: str, *, overwrite: bool = False, warn_if_exists: bool = True, output: bool = False, **action_kwargs) -> int:
    count = 0
    for src in planned_actions:
        if Path(src).exists():
            dst = planned_actions[src]
            if src != dst:
                dst_path = Path(dst)
                if not overwrite and dst_path.exists():
                    if warn_if_exists:
                        print(
                            f"Warning: {dst} exists, not overwiting with {src}")
                else:
                    if dst_path.exists():
                        if warn_if_exists:
                            print(
                                f"Warning: {dst} exists and is being overwritten with {src}")
                        delete(dst_path)
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    action_callable(src, dst, **action_kwargs)
                    if output:
                        print(f"{action_past_tense} <{src}> -> <{dst}>")
                    count += 1
    return count


def move_by_dict(planned_moves: dict[PathLike, PathLike], **move_kwargs) -> int:
    """Returns the number of items moved."""
    return __file_action_by_dict(planned_moves, shutil.move, "Moved", **move_kwargs)


def copy_by_dict(planned_copies: dict[PathLike, PathLike], **copy_kwargs) -> int:
    """Returns the number of items copied."""
    return __file_action_by_dict(planned_copies, shutil.copy2, "Copied", **copy_kwargs)


def remove_forbidden_chars(name: str, name_only=False):
    """ If name_only is True, then slashes and colons will also be removed. """
    if name_only:
        chars = r'\/:*?"<>|'+"\r\n"
    else:
        chars = '*?"<>|\r\n'
    for c in chars:
        name = name.replace(c, "")
    return name


class LinkException(Exception):
    pass


def link(src: PathLike, dst: PathLike, *, symbolic: bool = True, relativize=False, output=False):
    """ Creates a link at the path dst that targets the path at src.

    Automatically determines what kind of link to create based on whether or not src is a file or folder (raises and exception if src does not exist).

    If making a symbolic link and the source is a symbolic link, it is copied instead of linking to the existing link.

    If src is a relative path, it is absolutized for a non-symbolic link. For a symbolic link it is interpreted relative to the parent of dst (mimicking the behavior of the link itself) to check for existence and is applied to the resulting link as-is.

    On the other hand, if relativize = True is specified, an absolute path will be relativized for symbolic links. """

    # catch file existence problems early to distinguish them from permission problems
    src = Path(src)
    dst = Path(dst)

    if symbolic:
        if not src.is_absolute():
            rel_src = dst.parent.joinpath(src)
            if not rel_src.exists():
                raise LinkException(
                    f"File <{rel_src}> does not exist to link to (absolute path <{rel_src.resolve()}>)")
        else:
            if not src.exists():
                raise LinkException(f"File <{src}> does not exist to link to")
            rel_src = src
            if relativize:
                src = os.path.relpath(
                    str(src).removeprefix("\\\\?\\"), dst.parent)
        # if src is already a symlink, just copy it instead of linking to the existing link
        if rel_src.is_symlink():
            target = rel_src.readlink()
            if not target.is_absolute():
                target = rel_src.parent.joinpath(target).resolve()
            if output:
                print(
                    f"Found symbolic link <{rel_src}> to <{target}>, linking to that instead")
            rel_src = target
            src = target
        if rel_src.is_file():
            dst.symlink_to(src, target_is_directory=False)
            if output:
                print(f"Created symbolic link to file <{src}> at <{dst}>")
        else:
            dst.symlink_to(src, target_is_directory=True)
            if output:
                print(f"Created symbolic link to directory <{src}> at <{dst}>")
    else:
        if not src.exists():
            raise LinkException(f"File <{src}> does not exist to link to")
        if dst.exists():
            raise LinkException(f"File <{dst}> already exists")
        if src.is_file():
            dst.hardlink_to(src)
            if output:
                print(f"Created hard link to file <{src}> at <{dst}>")
        else:
            command = f"mklink /j \"{dst}\" \"{src}\""
            # capture output to hide it from console window, respecting output option
            subprocess.run(command, shell=True, capture_output=True)
            if output:
                print(f"Created junction to directory <{src}> at <{dst}>")


def relativize_link(link: PathLike):
    """ Silently ignores calls on non-symlink files (including hard links and junctions) or links that are already relative. """
    link = Path(link)
    if not link.is_symlink():
        return
    target = link.readlink()
    if target.is_absolute():
        # pathlib doesn't work for relative paths that would need ".."
        new_target = os.path.relpath(
            str(target).removeprefix("\\\\?\\"), link.parent)
        os.remove(link)
        link.symlink_to(new_target)


def absolutize_link(link: PathLike):
    """ Silently ignores calls on non-symlink files (including hard links and junctions) or links that are already absolute. """
    link = Path(link)
    if not link.is_symlink():
        return
    target = link.readlink()
    if not target.is_absolute():
        new_target = target.absolute()
        os.remove(link)
        link.symlink_to(new_target)


def delete(file: PathLike, not_exist_ok: bool = False, *, output: bool = False, ignore_errors: bool = False, **kwargs):
    """ Deletes files directly. Recursively deletes directory contents and then the directory itself. Works on symlinks, deleting the link without following it (leaves the link's destination intact). """

    def remove_respect_ignore_errors(file: Path):
        try:
            os.remove(file)
        except:
            if ignore_errors:
                if output:
                    print(f"Failed to delete {file}")
                    traceback.print_exc()
            else:
                raise

    def symlink_action(file: Path, depth: int):
        remove_respect_ignore_errors(file)
        if output:
            print(f"{'    ' * depth}{file}: deleted symbolic link")

    def not_exist_action(file: Path, depth: int):
        if not_exist_ok:
            if output:
                print(f"{'    ' * depth}{file}: already does not exist")
        else:
            # cause a FileNotFoundError
            os.remove(file)

    def dir_action(file: Path, depth: int):
        if output:
            print(f"{'    ' * depth}{file}: recursing into directory")

    def dir_post_action(file: Path, depth: int):
        os.rmdir(file)
        if output:
            print(f"{'    ' * depth}{file}: deleted directory ")

    def file_action(file: Path, depth: int):
        remove_respect_ignore_errors(file)
        if output:
            print(f"{'    ' * depth}{file}: deleted file ")

    prune_walk_kwargs(kwargs)
    walk(file, file_action=file_action, dir_action=dir_action, dir_post_action=dir_post_action,
         symlink_action=symlink_action, not_exist_action=not_exist_action, side_effects=True, **kwargs)


def delete_empty(root: PathLike = ".", output=True, ignore_errors=False):
    """ Returns the number of empty directories deleted """
    count = 0

    def delete_empty_recursive(root: Path, depth: int) -> bool:
        """ Returns whether the root argument was or became empty and was deleted """
        try:
            nonlocal count
            if root.is_file() or root.is_symlink():
                return False
            empty = True
            for f in root.iterdir():
                if not delete_empty_recursive(f, depth+1):
                    empty = False
            if empty:
                if output:
                    print("\t"*depth + str(root))
                root.rmdir()
                count += 1
            return empty
        except:
            if not ignore_errors:
                raise
            if output:
                print("\tError on "*depth + str(root))
            return False

    root = Path(root)
    delete_empty_recursive(root, 0)
    return count


class FileMismatchException(Exception):
    pass


def mirror(src: PathLike, dst: PathLike, *, output: bool = False, deleted_file_action: Callable[[PathLike], None] = delete, output_prefix="") -> int:
    """Returns the number of files changed (empty directories do not increase the count). Copies symbolic links instead of following them."""
    count = 0
    src = Path(src)
    dst = Path(dst)
    if (src.is_symlink() or src.exists()) and (dst.is_symlink() or dst.exists()):
        if src.is_symlink() != dst.is_symlink():
            raise FileMismatchException(
                f"One of {src} and {dst} is a symlink, the other is not")
        if not src.is_symlink() and src.is_dir() != dst.is_dir():
            # don't check for file vs. dir in case they are both symlinks,
            # since broken symlinks are always counted as files
            raise FileMismatchException(
                f"One of {src} and {dst} is a file, the other a directory")
    if src.is_symlink():
        if dst.is_symlink() or dst.exists():
            if src.readlink().resolve() != dst.readlink().resolve():
                if output:
                    print(f"{output_prefix}Updating symbolic link <\
                        {src}> -> <{dst}>")
                shutil.copy2(src, dst, follow_symlinks=False)
        else:
            if output:
                print(f"{output_prefix}Creating symbolic link <\
                    {src}> -> <{dst}>")
            shutil.copy2(src, dst, follow_symlinks=False)
    elif src.is_file():
        # copy file if newer
        # round to decrease precision to seconds (different file systems may save different precision)
        if not dst.exists():
            if output:
                print(f"{output_prefix}Creating file <{src}> -> <{dst}>")
            shutil.copy2(src, dst, follow_symlinks=False)
            count += 1
        elif int(src.stat().st_mtime) > int(dst.stat().st_mtime):
            # src is newer than dst
            if output:
                print(f"{output_prefix}Updating file <{src}> -> <{dst}>")
            shutil.copy2(src, dst, follow_symlinks=False)
            count += 1
    else:
        # src is dir
        if dst.exists():
            # delete files in dst that do not exist in src
            src_filenames = [f.name for f in src.iterdir()]
            to_delete = [f for f in dst.iterdir(
            ) if f.name not in src_filenames]
            for f in to_delete:
                if output:
                    print(f"{output_prefix}<{f}> was deleted")
                deleted_file_action(f)
                count += 1
        else:
            if output:
                print(f"{output_prefix}Creating folder <{dst}>")
            dst.mkdir()
        # recursively update files remaining
        for f in src.iterdir():
            count += mirror(f, dst.joinpath(f.name), output=output,
                            deleted_file_action=deleted_file_action, output_prefix=output_prefix+"    ")
    return count


def mirror_by_dict(mirror_dict: dict[PathLike, PathLike | Iterable[PathLike]], *, output=False):
    """Returns the number of files changed (empty directories do not increase the count)."""
    count = 0
    for src in mirror_dict:
        destinations = mirror_dict[src]
        if isinstance(destinations, Iterable) and not isinstance(destinations, str):
            for dst in destinations:
                count += mirror(src, dst, output=output)
        else:
            count += mirror(src, destinations, output=output)
    return count


def link_mirror(src: PathLike, dst: PathLike, *, output: bool = False, deleted_file_action: Callable[[PathLike], None] = delete, output_prefix="", symbolic=True) -> int:
    """Returns the number of files changed (empty directories do not increase the count). Directory structure is copied, but files are linked instead. Only creates absolute links."""
    count = 0
    src = Path(src).absolute()
    dst = Path(dst).absolute()
    if src.exists() and dst.exists() and src.is_dir() != dst.is_dir():
        raise FileMismatchException(
            f"One of {src} and {dst} is a file, the other a directory")
    if src.is_file():
        print(dst, dst.exists())
        if not dst.exists():
            if output:
                print(f"{output_prefix}Creating link <{src}> <- <{dst}>")
            link(src, dst, symbolic=symbolic)
            count += 1
    else:
        if dst.exists():
            # delete files in dst that do not exist in src
            src_filenames = [f.name for f in src.iterdir()]
            to_delete = [f for f in dst.iterdir(
            ) if f.name not in src_filenames]
            for f in to_delete:
                if output:
                    print(f"{output_prefix}<{f}> was deleted")
                deleted_file_action(f)
                count += 1
        else:
            if output:
                print(f"{output_prefix}Creating folder <{dst}>")
            dst.mkdir()
        # recursively update files remaining
        for f in src.iterdir():
            count += link_mirror(f, dst.joinpath(f.name), output=output,
                                 deleted_file_action=deleted_file_action, output_prefix=output_prefix+"    ")
    return count


def link_mirror_by_dict(mirror_dict: dict[PathLike, PathLike | Iterable[PathLike]], *, output=False, symbolic=True):
    """Returns the number of files changed (empty directories do not increase the count)."""
    count = 0
    for src in mirror_dict:
        destinations = mirror_dict[src]
        if isinstance(destinations, Iterable) and not isinstance(destinations, str):
            for dst in destinations:
                count += link_mirror(src, dst, output=output,
                                     symbolic=symbolic)
        else:
            count += link_mirror(src, destinations,
                                 output=output, symbolic=symbolic)
    return count


def two_way(path1: PathLike, path2: PathLike, *, output: bool = False, output_prefix=""):
    """Recursively compares the two paths specified. Newer files overwrite old ones, and files that don't exist on one side are copied from the other. Therefore does not handle deletions. Returns the number of files copied."""
    count = 0
    path1 = Path(path1)
    path2 = Path(path2)
    if path1.exists() and path2.exists() and path1.is_dir() ^ path2.is_dir():
        raise FileMismatchException(
            f"One of {path1} and {path2} is a file, the other a directory")
    if path1.exists() and path1.is_file():
        if path2.exists() and path2.is_file():
            # round to decrease precision to seconds (different file systems may save different precision)
            time1 = int(path1.stat().st_mtime)
            time2 = int(path2.stat().st_mtime)
            if time1 > time2:
                if output:
                    print(f"{output_prefix}Updating file <{
                          path1}> -> <{path2}>")
                shutil.copy2(path1, path2, follow_symlinks=False)
                count += 1
            elif time2 > time1:
                if output:
                    print(f"{output_prefix}Updating file <{
                          path2}> -> <{path1}>")
                shutil.copy2(path2, path1, follow_symlinks=False)
                count += 1
            # time may be the same, in which case nothing happens
        else:
            if output:
                print(f"{output_prefix}Creating file <{path1}> -> <{path2}>")
            shutil.copy2(path1, path2, follow_symlinks=False)
            count += 1
    elif path2.exists() and path2.is_file():
        # assert not path1.exists()
        if output:
            print(f"{output_prefix}Creating file <{path2}> -> <{path1}>")
        shutil.copy2(path2, path1, follow_symlinks=False)
        count += 1
    else:
        # directories
        # recursively update files remaining
        names = set()
        if path1.exists():
            names |= {f.name for f in path1.iterdir()}
        else:
            path1.mkdir(parents=True, exist_ok=True)
        if path2.exists():
            names |= {f.name for f in path2.iterdir()}
        else:
            path2.mkdir(parents=True, exist_ok=True)
        for n in names:
            count += two_way(path1.joinpath(n), path2.joinpath(n), output=output,
                             output_prefix=output_prefix+"    ")
    return count


class ZipException(Exception):
    pass


def zip(zip_path: PathLike, files: Iterable[PathLike], relative_root: PathLike | None = None, *, overwrite: bool = True, exclude: Iterable[str] = []):
    """ Zip a set of files using LZMA. If the path doesn't end with .zip, the extension is added automatically for convenience.

    exclude is a list of regular expressions applied to full file paths with backslahes replaced with forward slashes. Matching files are not zipped. If a directory matches, none of its contents are zipped. Respects whether the original arguments were relative or absolute for this purpose. """
    def recursive_zip(files: Iterable[Path], zip: ZipFile, relative_root: Path, exclude: Iterable[str]):
        for f in files:
            skip = False
            for e in exclude:
                if re.fullmatch(e, str(f).replace("\\", "/")):
                    skip = True
                    break
            if skip:
                continue
            if f.is_file():
                zip.write(f, arcname=f.relative_to(relative_root))
            else:
                recursive_zip(f.iterdir(), zip, relative_root, exclude)

    zip_path = Path(zip_path).with_suffix(".zip")
    if relative_root is None:
        relative_root = zip_path.parent
    else:
        relative_root = Path(relative_root)
    files = [Path(f) for f in files]
    for f in files:
        if not (relative_root in f.parents or (relative_root == f and f.is_dir())):
            raise ZipException(
                f"Relative root <{relative_root}> is not a parent of <{f}>")
        if f in zip_path.parents or f == zip_path:
            raise ZipException(
                f"<{f}> is a parent of the zip target <{zip_path}>")
    if overwrite:
        mode = "w"
    else:
        mode = "a"
    # use LZMA like 7-zip
    with ZipFile(zip_path, mode, zipfile.ZIP_DEFLATED) as zip:
        recursive_zip(files, zip, relative_root, exclude)


def unzip(zip_path: PathLike, files: Iterable[PathLike] | None = None,  output_dir: PathLike | None = None, *, overwrite: bool = False):
    """ Unzip a set of files. If the path doesn't end with .zip, the extension is added automatically for convenience. If a set of files is not specified, all of them are extracted."""
    zip_path = Path(zip_path).with_suffix(".zip")
    if output_dir == None:
        # controls unzip destination
        output_dir = zip_path.parent
    output_dir = Path(output_dir)
    with ZipFile(zip_path, "r") as zip:
        if files is None:
            files = zip.namelist()
        else:
            files: list[str] = [str(f) for f in files]
        if not overwrite:
            files = [
                f for f in files if not output_dir.joinpath(f).exists()]
        zip.extractall(output_dir,  files)


def flatten(root: PathLike = ".", *, output=True, **kwargs):
    """ Moves all files in subfolders so they are directly inside the root folder, and then deletes the leftover empty subfolders. """

    root = Path(root)

    moves = {}

    def file_action(p: Path, d: int):
        if d == 0:
            return
        moves[p] = root.joinpath(p.name)

    prune_walk_kwargs(kwargs)
    walk(root=root, file_action=file_action, side_effects=True)
    move_by_dict(moves, output=output)
    delete_empty(root, output=output)


def watch(file: PathLike, callback: Callable[[Path, float | None], None], poll_time: float = 5, output=False, time_format="%Y %B %d, %H:%M:%S"):
    """Monitor a file for changes by periodically checking if its modification time has changed (every 5 seconds by default) (not necessarily increasing, such as if an old copy of the file was moved into the original location). Provides the callback function with the file and its new modification time. Optionally, can also print out that the file was updated and when. If the file does not exist and then is created, or if it is deleted, that counts as an update. """
    file = Path(file)

    # None guaranteed not to come up as an actual file modification time, so non-existence is always not equal to any actual time

    last_mod_time = os.stat(file).st_mtime if file.exists() else None

    while True:
        current_mod_time = os.stat(file).st_mtime if file.exists() else None

        if current_mod_time != last_mod_time:
            if output:
                print(
                    f"File <{file}> was updated at <{time.strftime(time_format, time.gmtime(current_mod_time))}>")
            callback(file, current_mod_time)
            last_mod_time = current_mod_time

        time.sleep(poll_time)


def regex_rename(find: str | re.Pattern[str], replace: str | Callable[[str | re.Match], str], root: PathLike = ".", *, output: bool = False, **kwargs):
    """ Only moves files. Returns the number of files moved. """
    find = re.compile(find)
    moves = {}

    def file_action(p: Path, i: int):
        new_name = re.sub(find, replace, p.name)
        if p.name != new_name:
            moves[p] = p.with_name(new_name)

    prune_walk_kwargs(kwargs)
    walk(root, file_action=file_action, side_effects=True, **kwargs)

    return move_by_dict(moves, output=output)


if WINDOWS:
    import msvcrt

    class LockFile:
        """ Based on Thomas Lux's answer on https://stackoverflow.com/questions/489861/locking-a-file-in-python """

        def __lock_file(self):
            self.locked_size = max(os.stat(self.path).st_size, 1)
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, self.locked_size)

        def __unlock_file(self):
            msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, self.locked_size)

        def __init__(self, path: PathLike, *args, **kwargs):
            self.path = path
            self.fd: io.IOBase = open(path, *args, **kwargs)
            self.__lock_file()

        def __enter__(self):
            """ Implement context manager """
            return self.fd

        def __exit__(self, exc_type, exc_val, exc_tb):
            """ Implement context manager """
            self.__unlock_file()
            self.fd.close()
            # do not suppress exceptions
            return False

        def close(self):
            """ For explicit closing when not used as a context manager """
            self.__exit__(None, None, None)

        def __getattr__(self, name):
            """ Redirect other attributes to the internal opened file. """
            return getattr(self.fd, name)

    def open_locked(file: Path, *args, **kwargs) -> LockFile:
        """ Only prevents multiple open instances if this function is used every time a given file is opened instead of only the builtin open. Still prevents external accesses (e.g. via the file explorer). """
        return LockFile(file, *args, **kwargs)
