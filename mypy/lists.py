from typing import Generator, Iterable


def read_file_lists(filename: str, list_sep: str = ",", comment: str = "#") -> Generator:
    with open(filename) as file:
        for line in file:
            line = line.strip()
            if line == "" or line[:len(comment)] == comment:
                continue
            yield line.split(list_sep)


def write_file_lists(filename: str, lists: Iterable[Iterable], list_sep: str = ",") -> None:
    with open(filename, "w", encoding="UTF-8") as f:
        for l in lists:
            first = True
            for i in l:
                if first:
                    first = False
                else:
                    f.write(list_sep)
                f.write(i)
            f.write("\n")


def remove_duplicates_in_place(l: list) -> list:
    """Still uses sets, but preserves the order of the remaining elements, which turning into a set and then back would not."""
    unique = set()
    i = 0
    while i < len(l):
        if l[i] in unique:
            del l[i]
        else:
            unique.add(l[i])
            i += 1
    return l
