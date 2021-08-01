import re
from math import floor
from os import path, sep, walk
from os.path import basename
from pathlib import Path
from random import Random
from re import Match, compile, fullmatch
from shutil import move
from typing import Iterable

from mypy import dictionaries, files


def name_and_ext(file_name: str) -> tuple[str, str]:
    lbr = file_name.rfind("[")
    rbr = file_name.rfind("]")
    if rbr != -1 and lbr != -1 and lbr < rbr:
        # existing tags
        name = file_name[:lbr]
        ext = file_name[rbr + 1:]
    else:
        # no existing tags
        dot = file_name.rfind(".")
        name = file_name[:dot]
        ext = file_name[dot:]
    return (name, ext)


def add_tags(file_name: str, new_tags: set[str]) -> str:
    return set_tags(file_name, get_tags(file_name) | new_tags)


def remove_tags(file_name: str, remove_tags: set[str]) -> str:
    tags = get_tags(file_name) - remove_tags
    return set_tags(file_name, tags)


def set_tags(file_name: str, tags: set[str]) -> str:
    name, ext = name_and_ext(file_name)
    if len(tags) == 0:
        return name + ext
    tags_str = ""
    first = True
    for tag in sorted(tags):
        if first:
            first = False
        else:
            tags_str += " "
        tags_str += tag
    return name + "[" + tags_str + "]" + ext


def get_tags(file_name: str) -> set[str]:
    lbr = file_name.rfind("[")
    rbr = file_name.rfind("]")
    tags = set()
    if rbr != -1 and lbr != -1 and lbr < rbr:
        for tag in file_name[lbr + 1:rbr].split(" "):
            if tag == "" or tag.isspace():
                continue
            tags.add(tag.lower())
    return tags


def set_name(file_name_with_tags: str, new_name: str) -> str:
    name, ext = name_and_ext(file_name_with_tags)
    tags_and_ext = file_name_with_tags[len(name):]
    return new_name + tags_and_ext


def collect_tags(root: str, priority_dirs: Iterable[str], collected_tags_file: str) -> None:
    known_tags = {}
    priority_tags = set()

    for dirpath, dirnames, filenames in files.conditional_walk(root, files.ignore_dot_dirs):
        # get tags
        for f in filenames:
            for tag in get_tags(f):
                if tag not in known_tags:
                    known_tags[tag] = set()

    # find dirs that match tags
    for dirpath, dirnames, filenames in files.conditional_walk(root, files.ignore_dot_dirs):
        # if tag is among those in the directory path, associate the directory with the tag
        is_pdir = False
        for pdir in priority_dirs:
            if pdir in dirpath:
                is_pdir = True

        for tag in known_tags:
            if tag in basename(dirpath).split(" "):
                # add * if it's a priority dir
                known_tags[tag].add(f"{'*' if is_pdir else ''}{dirpath}")

    # find priority tags/dirs
    # see if tag is in a folder name in a priority directory, if so add a * to the tag
    for pdir in priority_dirs:
        for dirpath, dirnames, filenames in files.conditional_walk(root + sep + pdir, files.ignore_dot_dirs):
            for subdir in dirnames:
                for tag in sorted(known_tags):
                    if tag in subdir.split(" "):
                        priority_tags.add(tag)
            break

    # add *s to priority tags
    for tag in priority_tags:
        star_tag = f"*{tag}"
        known_tags[star_tag] = known_tags[tag]
        del known_tags[tag]

    dictionaries.write_file_dict(collected_tags_file, known_tags)


def update_tags(root: str, known_tags_file: str, tag_regex_file: str = None, tag_subsets_file: str = None) -> None:
    # find tags in names (including tag aliases), convert aliases, add tags that should be supersets of other tags, and sort
    known_tags = set()
    tag_regex = {}
    # dict key is a subset of val
    tag_subsets = {}

    for tag in dictionaries.read_file_dict(known_tags_file):
        known_tags.add(tag.removeprefix("*"))

    tag_regex = dictionaries.read_file_dict(tag_regex_file, key_value_sep=">>")

    tag_subsets = dictionaries.flip_dict(
        dictionaries.read_file_dict(tag_subsets_file))

    planned_moves = {}

    for dirpath, dirnames, filenames in walk(root):
        # get tags
        for f in filenames:
            file_tags = get_tags(f)
            name, ext = name_and_ext(f)

            """ # find tags and aliases in front part of file name
            for tag in known_tags:
                if len(tag) > 3:
                    # ignore tags <= 3 chars, strong chance of accidental inclusion on unrelated words
                    if tag in name.lower().replace(" ", "_").replace("-", "_") and tag not in file_tags:
                        file_tags.add(tag) """

            # remove, convert aliases
            new_tags = set()
            for tag in file_tags:
                regex_replaced = False
                for regex in tag_regex:
                    regex = regex.lower()
                    if re.search(regex, tag):
                        regex_replaced = True
                        new_tags.add(
                            re.sub(regex, tag_regex[regex], tag).replace(" ", "_"))
                if not regex_replaced:
                    new_tags.add(tag)
            if "" in new_tags:
                new_tags.remove("")
            file_tags = new_tags

            # add superset tags
            new_tags = set()
            for tag in file_tags:
                new_tags.add(tag)
                if tag in tag_subsets:
                    new_tags.add(tag_subsets[tag])
            file_tags = new_tags

            # sort
            new_name = set_tags(f, file_tags)
            if f != new_name:
                planned_moves[dirpath + sep + f] = dirpath + sep + new_name

    files.move_by_dict(planned_moves)


def move_by_tags(root: str, priority_dirs: Iterable[str], known_tags_file: str) -> None:
    known_tags = dictionaries.read_file_dict(known_tags_file, all_lists=True)

    planned_moves = {}

    for dirpath, dirnames, filenames in files.conditional_walk(root, files.ignore_dot_dirs):
        # for each file, find all the places it can go
        for f in filenames:
            has_priority_tag = False
            target_dirs = set()
            for tag in get_tags(f):
                if tag in known_tags:
                    target_dirs |= set(known_tags[tag])
                elif "*"+tag in known_tags:
                    target_dirs |= set(known_tags["*"+tag])
                    priority_tag = tag
                    has_priority_tag = True

            # if has a priority tag can only go into priority folders (will always be at least one), if not cannot go into priority folders
            new_target_dirs = set()
            if has_priority_tag:
                for d in target_dirs:
                    if d[0] == "*":
                        new_target_dirs.add(d[1:])
            else:
                for d in target_dirs:
                    if d[0] != "*":
                        new_target_dirs.add(d)
            target_dirs = new_target_dirs

            # choose the deepest, most specific possibile folder (that is in the priority tag's folder if there is one) -- unless multiple are tied for depth and have a common ancestor, in which case that ancestor is used
            first = True
            for dir in target_dirs:
                # ensure goes to right priority folder
                if has_priority_tag and priority_tag not in dir:
                    continue
                sep_count = dir.removesuffix(sep).count(sep)
                if first or sep_count > max_depth:
                    # dir greater depth, new max, clear set
                    max_depth = sep_count
                    max_depth_dirs = {dir}
                    first = False
                elif sep_count == max_depth:
                    # matching depth, add dir
                    max_depth_dirs.add(dir)

            # if no possible target locations (usually if no tags in the first place) nothing happens
            # if there was a least one possible target
            if not first:
                target = os.path.commonpath(max_depth_dirs)
                if dirpath != target:
                    planned_moves[dirpath + sep + f] = target + sep + f

    files.move_by_dict(planned_moves)


def random_number_rename(root: str, re_str: str, rand_max: int) -> None:
    r = Random()
    r.seed()

    regex = compile(re_str)

    planned_moves = {}

    for dirpath, dirnames, filenames in walk(root):
        for f in filenames:
            name, ext = name_and_ext(f)
            if regex.fullmatch(name) != None:
                planned_moves[dirpath + path.sep + f] = dirpath + \
                    path.sep + set_name(f, str(floor(r.random()*1000000)))

    for src in planned_moves:
        move("\\\\?\\" + src, "\\\\?\\" + planned_moves[src])


def tag_all_in(root: str, new_tags: set[str], visit_subdirs: bool = True) -> None:
    planned_moves = {}

    for dir_path, subdirs, files in walk(root):
        for f in files:
            new_name = add_tags(f, new_tags)
            if f != new_name:
                planned_moves[dir_path + path.sep +
                              f] = dir_path + path.sep + new_name
        if not visit_subdirs:
            break

    files.move_by_dict(planned_moves)
