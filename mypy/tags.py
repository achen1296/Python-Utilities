import os

from mypy import files


def name_and_ext(filename: str) -> tuple[str, str]:
    lbr = filename.rfind("[")
    rbr = filename.rfind("]")
    if rbr != -1 and lbr != -1 and lbr < rbr:
        # existing tags
        name = filename[:lbr]
        ext = filename[rbr + 1:]
    else:
        # no existing tags
        dot = filename.rfind(".")
        name = filename[:dot]
        ext = filename[dot:]
    return (name, ext)


def add(filename: str, new_tags: set[str]) -> str:
    return set(filename, get(filename) | new_tags)


def remove(filename: str, remove_tags: set[str]) -> str:
    return set(filename, get(filename) - remove_tags)


def set(filename: str, tags: set[str]) -> str:
    name, ext = name_and_ext(filename)
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


def get(filename: str) -> set[str]:
    lbr = filename.rfind("[")
    rbr = filename.rfind("]")
    tags = set()
    if rbr != -1 and lbr != -1 and lbr < rbr:
        for tag in filename[lbr + 1:rbr].split(" "):
            tag = tag.strip()
            if tag == "":
                continue
            tags.add(tag.lower())
    return tags


def set_name(filename: str, new_name: str) -> str:
    name, ext = name_and_ext(filename)
    return new_name + filename[len(name):]


def tag_all_in(root: os.PathLike, new_tags: set[str], visit_subdirs: bool = True) -> None:
    planned_moves = {}

    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            new_name = add(f, new_tags)
            if f != new_name:
                planned_moves[dirpath + os.sep +
                              f] = dirpath + os.sep + new_name
        if not visit_subdirs:
            break

    files.move_by_dict(planned_moves)
