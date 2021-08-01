from typing import Iterable


def read_file_lists(filename: str, list_sep: str = "|", comment: str = "#") -> list:
    with open(filename) as file:
        for line in file:
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            yield line.split(list_sep)


def write_file_lists(filename: str, lists: Iterable[Iterable], list_sep: str = "|") -> None:
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
