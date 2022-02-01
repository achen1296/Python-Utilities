from io import TextIOWrapper
from typing import TextIO


def nest(exp: str, levels: int, f: TextIO):
    e1 = f"\\left(f_{{1}}{exp},g_{{1}}{exp}\\right)"
    e2 = f"\\left(f_{{2}}{exp},g_{{2}}{exp}\\right)"
    if levels <= 1:
        f.write(e1+"\n")
        f.write(e2+"\n")
        return
    nest(e1, levels-1, f)
    nest(e2, levels-1, f)


with open("tree.txt", "w") as f:
    nest("\\left(f\\left(t\\right),g\\left(t\\right)\\right)", 7, f)
