# (c) Andrew Chen (https://github.com/achen1296)

from pathlib import Path
from typing import Callable, Iterable

from more_itertools import consume

from .consts import *
from .stats import *


def yield_file(f: Path, _):
    yield f


if WINDOWS:
    import stat

    def hidden(file: PathLike):
        return os.stat(file).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN != 0
else:
    def hidden(file: PathLike):
        Path(file).name.startswith(".")


def walk[T](root: PathLike = ".", *,
            file_action: Callable[[Path, int],
                                  Iterable[T] | None] | None = yield_file,
            skip_dir: Callable[[Path, int], bool] | None = None,
            dir_action: Callable[[Path, int], Iterable[T] | None] | None = None,
            dir_post_action: Callable[[Path, int], Iterable[T] | None] | None = None,
            symlink_action: Callable[[Path, int], Iterable[T] | None] | None = None,
            not_exist_action: Callable[[Path, int],
                                       Iterable[T] | None] | None = None,
            error_action: Callable[[Path, int, Exception],
                                   Iterable[T] | None] | None = None,
            side_effects: bool = False,
            ignore_hidden: bool = False,
            ) -> Iterable[T]:
    """ For directories, dir_action is called first. Then skip_dir is called, and if returns a truthy value nothing else happens to the directory. Otherwise, the contents are recursively walked over before dir_post_action is called.

    If symlink_action is not specified, symlinks are treated like the kind of file it points to (or as a file if the link is broken). If symlink_action is specified, then only that will be used on symlinks.

    The second argument to each action is the depth from the root, which has depth 0.

    For all actions (skip_dir is not an action), if the return value is not None, it is yielded from -- so it must be iterable. This is to support using this function as a generator. However, this means that if it is intended to be used only for side effects, the generator must be consumed -- specify side_effects = True, which will also result in a None return value. """

    def walk_recursive(root: Path, depth: int):
        try:
            if ignore_hidden and hidden(root):
                return
            if symlink_action is not None and root.is_symlink():
                if (symlink_result := symlink_action(root, depth)) is not None:
                    yield from symlink_result
            elif not root.exists() and not root.is_symlink():
                # check for symlinks again to make broken symlinks to fall through to the file action
                if not_exist_action is not None and (not_exist_result := not_exist_action(root, depth)) is not None:
                    yield from not_exist_result
            elif root.is_file() or (root.is_symlink() and not root.exists()):
                if file_action is not None and (file_result := file_action(root, depth)) is not None:
                    yield from file_result
            else:
                # assert root.is_dir()
                if dir_action is not None and (dir_result := dir_action(root, depth)) is not None:
                    yield from dir_result
                if skip_dir is None or not skip_dir(root, depth):
                    for f in root.iterdir():
                        yield from walk_recursive(f, depth+1)
                    if dir_post_action is not None and (dir_post_result := dir_post_action(root, depth)) is not None:
                        yield from dir_post_result
        except Exception as x:
            if error_action is not None:
                error_action(root, depth, x)
            else:
                raise

    gen = walk_recursive(Path(root), 0)
    if side_effects:
        consume(gen)
        return []
    else:
        return gen


WALK_ACTIONS = [a+"_action" for a in ["file", "dir",
                                      "dir_post", "symlink", "not_exist", "error"]] + ["side_effects"]


def prune_walk_kwargs(kwargs):
    """ Remove _action kwargs and also side_effects, since these are usually set specially by functions using walk. """
    for w in WALK_ACTIONS:
        if w in kwargs:
            del kwargs[w]
