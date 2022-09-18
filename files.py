import hashlib
import os
import re
import shutil
import typing
import zipfile
from pathlib import Path
from zipfile import ZipFile


def create_file(path: os.PathLike, binary=False, **open_kwargs):
    """ The last piece of the path is assumed to be a file, even if it doesn't have an extension (otherwise use os.makedirs). open_kwargs passed to open(), the result of which is returned. """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        mode = "wb"
    else:
        mode = "w"
    return open(path, mode, **open_kwargs)


def ignore_dot(dirpath: str, dirnames: list[str], filenames: list[str]) -> bool:
    """ For use with conditional_walk as a condition. Ignores directories/files that start with a ., the Unix hidden file convention. """
    return Path(dirpath).name[0] != "."


def conditional_walk(root: os.PathLike, condition: typing.Callable[[str, list[str], list[str]], bool] = None) -> tuple[str, list[str], list[str]]:
    """ Wraps os.walk, only returning the directory information that passes the condition (when the provided function returns true), skipping children of those that fail. """
    if condition is None:
        def condition(dp, dns, fns): return True
    for dirpath, dirnames, filenames in os.walk(root):
        # ignore folders not matching the condition
        if not condition(dirpath, dirnames, filenames):
            # skip all subdirs too
            dirnames[:] = []
            continue
        yield (dirpath, dirnames, filenames)


def __file_action_by_dict(planned_actions: dict[os.PathLike, os.PathLike], action_callable: typing.Callable[[os.PathLike, os.PathLike], None], action_past_tense: str, *, overwrite: bool = False, warn_if_exists: bool = True, output: bool = False, **kwargs) -> int:
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
                    action_callable(src, dst, **kwargs)
                    if output:
                        print(f"{action_past_tense} <{src}> -> <{dst}>")
                    count += 1
    return count


def move_by_dict(planned_moves: dict[os.PathLike, os.PathLike], **kwargs) -> int:
    """Returns the number of items moved."""
    return __file_action_by_dict(planned_moves, shutil.move, "Moved", **kwargs)


def copy_by_dict(planned_copies: dict[os.PathLike, os.PathLike], **kwargs) -> None:
    """Returns the number of items copied."""
    return __file_action_by_dict(planned_copies, shutil.copy2, "Copied", **kwargs)


def remove_forbidden_chars(name: str, name_only=False):
    """ If name_only is True, then slashes and colons will also be removed. """
    if name_only:
        chars = r'\/:*?"<>|'+"\r\n"
    else:
        chars = '*?"<>|'
    for c in chars:
        name = name.replace(c, "")
    return name


class LinkException(Exception):
    pass


def link(src: os.PathLike, dst: os.PathLike, *, symbolic: bool = True):
    """ Leave mode as None to automatically determine whether to use a link for a file or for a directory. If a symbolic link is requested and the source is a symbolic link, it is copied instead of linking to the existing link. """

    # catch file existence problems early to distinguish them from permission problems
    src = Path(src)
    dst = Path(dst)

    if symbolic:
        if not src.is_absolute():
            rel = dst.parent.joinpath(src)
            if not rel.exists():
                raise LinkException(
                    f"File <{rel}> does not exist to link to (absolute path <{rel.resolve()}>)")
        else:
            if not src.exists():
                raise LinkException(f"File <{src}> does not exist to link to")
            rel = src
        # if src is already a symlink, just copy it instead of linking to the existing link
        if rel.is_symlink():
            if symbolic:
                shutil.copy2(rel, dst, follow_symlinks=False)
            else:
                raise LinkException(
                    f"{rel} is a symlink and a non-symbolic link was requested.")
        if rel.is_file():
            dst.symlink_to(src, target_is_directory=False)
        else:
            dst.symlink_to(src, target_is_directory=True)
    else:
        if not src.exists():
            raise LinkException(f"File <{src}> does not exist to link to")
        if dst.exists():
            raise LinkException(f"File <{dst}> already exists")
        if src.is_file():
            src.link_to(dst)
        else:
            command = f"mklink /j \"{dst}\" \"{src}\""
            result = os.system(command)
            if result != 0:
                raise OSError(f"{command} resulted in an error")


def relativize_link(link: os.PathLike):
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


def absolutize_link(link: os.PathLike):
    link = Path(link)
    if not link.is_symlink():
        return
    target = link.readlink()
    if not target.is_absolute():
        new_target = target.absolute()
        os.remove(link)
        link.symlink_to(new_target)


def delete(file: os.PathLike, not_exist_ok=False, *, output=False):
    """Uses either os.remove or shutil.rmtree as appropriate."""
    path = Path(file)
    if path.is_symlink():
        os.remove(path)
        if output:
            print(f"Deleted symbolic link {path}")
    elif not path.exists() and not_exist_ok:
        if output:
            print(f"{path} already doesn't exist")
        # else will raise an error on attempting one of the operations below
        return
    elif path.is_dir():
        shutil.rmtree(path)
        if output:
            print(f"Deleted directory {path}")
    else:
        os.remove(path)
        if output:
            print(f"Deleted file {path}")


class FileMismatchException(Exception):
    pass


def mirror(src: os.PathLike, dst: os.PathLike, *, output: bool = False, deleted_file_action: typing.Callable[[os.PathLike], None] = delete, output_prefix="") -> int:
    """Returns the number of files changed (empty directories do not increase the count). Copies symbolic links instead of following them."""
    count = 0
    src = Path(src)
    dst = Path(dst)
    if src.exists() and dst.exists() and src.is_dir() ^ dst.is_dir():
        raise FileMismatchException(
            f"One of {src} and {dst} is a file, the other a directory")
    if src.is_file():
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
        #src is dir
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
            dst.mkdir()
        # recursively update files remaining
        for f in src.iterdir():
            count += mirror(f, dst.joinpath(f.name), output=output,
                            deleted_file_action=deleted_file_action, output_prefix=output_prefix+"    ")
    return count


def mirror_by_dict(mirror_dict: dict[os.PathLike, typing.Union[os.PathLike, typing.Iterable[os.PathLike]]], *, output=False):
    """Returns the number of files changed (empty directories do not increase the count)."""
    count = 0
    for src in mirror_dict:
        destinations = mirror_dict[src]
        if isinstance(destinations, typing.Iterable):
            for dst in destinations:
                count += mirror(src, dst, output=output)
        else:
            count += mirror(src, destinations, output=output)
    return count


def two_way(path1: os.PathLike, path2: os.PathLike, *, output: bool = False, output_prefix=""):
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
                    print(f"{output_prefix}Updating file <{path1}> -> <{path2}>")
                shutil.copy2(path1, path2, follow_symlinks=False)
                count += 1
            elif time2 > time1:
                if output:
                    print(f"{output_prefix}Updating file <{path2}> -> <{path1}>")
                shutil.copy2(path2, path1, follow_symlinks=False)
                count += 1
            # time may be the same, in which case nothing happens
        else:
            if output:
                print(f"{output_prefix}Creating file <{path1}> -> <{path2}>")
            shutil.copy2(path1, path2, follow_symlinks=False)
            count += 1
    elif path2.exists() and path2.is_file():
        #assert not path1.exists()
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


def _recursive_zip(files: typing.Iterable[Path], zip: ZipFile, relative_root: Path, exclude: set[Path]):
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
            _recursive_zip(f.iterdir(), zip, relative_root, exclude)


class ZipException(Exception):
    pass


def zip(zip_path: os.PathLike, files: typing.Iterable[os.PathLike], relative_root: os.PathLike = None, *, overwrite: bool = True, exclude: list[str] = []):
    """ Zip a set of files using LZMA. If the path doesn't end with .zip, the extension is added automatically for convenience. 

    exclude is a list of regular expressions applied to full file paths with backslahes replaced with forward slashes. Matching files are not zipped. If a directory matches, none of its contents are zipped. Respects whether the original arguments were relative or absolute for this purpose. """
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
        _recursive_zip(files, zip, relative_root, exclude)


def unzip(zip_path: os.PathLike, files: typing.Iterable[os.PathLike] = None,  output_dir: os.PathLike = None, *, overwrite: bool = False):
    """ Unzip a set of files using 7-zip. If the path doesn't end with .zip, the extension is added automatically for convenience. If a set of files is not specified, all of them are extracted."""
    zip_path = Path(zip_path).with_suffix(".zip")
    if output_dir == None:
        # controls unzip destination
        output_dir = zip_path.parent
    output_dir = Path(output_dir)
    with ZipFile(zip_path, "r") as zip:
        if not overwrite:
            if files is None:
                files = zip.namelist()
            files = [f for f in files if not output_dir.joinpath(f).exists()]
        zip.extractall(output_dir, files)


def long_names(root: os.PathLike) -> set[str]:
    """ Returns a set of files whose absolute paths are >= 260 characters, which means they are too long for some Windows applications. Not > 260 because, as the page linked below describes, Windows includes the NUL character at the end in the count, while Python strings do not.

    docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation """
    root = Path(root).resolve()
    long_set = set()
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            full = dirpath+os.sep+f
            if len(full) >= 260:
                long_set.add(full)
    return long_set


def re_split(file: os.PathLike, separator: str = "\s*\n\s*", *, exclude_empty: bool = True, encoding="utf8", **open_kwargs):
    """Like re.split() but does not load the whole file as a string all at once."""
    try:
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
    except FileNotFoundError:
        return


def id(file: os.PathLike):
    return os.stat(file).st_ino


def size(file: os.PathLike):
    return os.stat(file).st_size


def hash(file: os.PathLike, size: int = -1, hex: bool = True) -> int:
    with open(file, "rb") as f:
        h = hashlib.sha3_256(f.read(size))
        return h.hexdigest() if hex else h.digest()


def is_empty(root: os.PathLike) -> bool:
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


def delete_empty(root: os.PathLike):
    def delete_empty_recursive(root: Path) -> bool:
        """ Returns whether the root argument was or became empty and was deleted """
        if root.is_file():
            return False
        empty = True
        for f in root.iterdir():
            if not delete_empty_recursive(f):
                empty = False
        if empty:
            root.rmdir()
        return empty

    root = Path(root)
    delete_empty_recursive(root)


def list_files(root: os.PathLike, condition: typing.Callable[[str, list[str], list[str]], bool] = None):
    result = []
    for dirpath, dirnames, filenames in conditional_walk(root, condition):
        result += [dirpath + os.sep + f for f in filenames]
    return result
