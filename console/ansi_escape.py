# (c) Andrew Chen (https://github.com/achen1296)

# en.wikipedia.org/wiki/ANSI_escape_code
# learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences
# all of these functions print directly to the console because they are not supposed to be used anywhere else anyway

from enum import Enum
from shutil import get_terminal_size


def measure_lines(text: str, terminal_width: int | None = None):
    """ Measure how many lines tall the text would be in a terminal of the given width. If not given a terminal width, gets the current one. """
    if terminal_width is None:
        terminal_width = get_terminal_size().columns
    lines = text.split("\n")
    count = len(lines)
    for l in lines:
        len_l = len(l)
        if len_l == 0:
            # avoid negatives in the equation below
            continue
        # decrement length because exactly filling the terminal does not go onto the next line
        count += (len_l - 1) // terminal_width
    return count


ESC = "\x1b"
ST = ESC + "\\"


def bell():
    """Print the "bell" character. """
    print('\u0007', end="")


def cursor_reverse_index():
    print(f"{ESC}M", end="")


def cursor_save():
    print(f"{ESC}7", end="")


def cursor_restore():
    print(f"{ESC}8", end="")


class CursorMoveException(Exception):
    pass


def _check_cursor_move(i: int):
    if not 0 <= i <= 32767:
        raise CursorMoveException(
            "Cursor move argument must be between 0 and 32767 inclusive.")


def cursor_up(i: int = 1):
    # 0 is treated as 1 if sent normally!
    if i == 0:
        return
    _check_cursor_move(i)
    print(f"{ESC}[{i}A", end="")


def cursor_down(i: int = 1):
    # 0 is treated as 1 if sent normally!
    if i == 0:
        return
    _check_cursor_move(i)
    print(f"{ESC}[{i}B", end="")


def cursor_forward(i: int = 1):
    # 0 is treated as 1 if sent normally!
    if i == 0:
        return
    _check_cursor_move(i)
    print(f"{ESC}[{i}C", end="")


def cursor_back(i: int = 1):
    # 0 is treated as 1 if sent normally!
    if i == 0:
        return
    _check_cursor_move(i)
    print(f"{ESC}[{i}D", end="")


def cursor_next_line(i: int = 1):
    # 0 is treated as 1 if sent normally!
    if i == 0:
        return
    _check_cursor_move(i)
    print(f"{ESC}[{i}E", end="")


def cursor_previous_line(i: int = 1):
    # 0 is treated as 1 if sent normally!
    if i == 0:
        return
    _check_cursor_move(i)
    print(f"{ESC}[{i}F", end="")


def cursor_horizontal_absolute(i: int = 1):
    """ Note that 0 is treated as 1 """
    _check_cursor_move(i)
    print(f"{ESC}[{i}G", end="")


def cursor_vertical_absolute(i: int = 1):
    """ Note that 0 is treated as 1 """
    _check_cursor_move(i)
    print(f"{ESC}[{i}d", end="")


def cursor_set_position(x: int = 1, y: int = 1):
    """ Note that 0 is treated as 1 for both coordinates """
    _check_cursor_move(x)
    _check_cursor_move(y)
    print(f"{ESC}[{y};{x}H", end="")


"""def get_cursor_position() -> tuple[int, int]:
    print(f"{ESC}[6n", end="", flush=False)
    pos_str = ""
    while (c := sys.stdin.read(1)) != "R":
        pos_str += c
    assert pos_str[0:1] == ESC + "["
    y, x = pos_str.split(";")
    return int(x), int(y) """


def cursor_blink(blink: bool = True):
    if blink:
        print(f"{ESC}[?12h", end="")
    else:
        print(f"{ESC}[?12l", end="")


def cursor_show(show: bool = True):
    if show:
        print(f"{ESC}[?25h", end="")
    else:
        print(f"{ESC}[?25l", end="")


class CursorShape(Enum):
    DEFAULT = 0
    BLINKING_BLOCK = 1
    STEADY_BLOCK = 2
    BLINKING_UNDERLINE = 3
    STEADY_UNDERLINE = 4
    BLINKING_BAR = 5
    STEADY_BAR = 6


def cursor_shape(shape: CursorShape):
    print(f"{ESC}[{shape.value} q", end="")


def scroll_down(i: int = 1):
    print(f"{ESC}[{i}S", end="")


def scroll_up(i: int = 1):
    print(f"{ESC}[{i}T", end="")


def insert_characters(i: int = 1):
    print(f"{ESC}[{i}@", end="")


def delete_characters(i: int = 1):
    print(f"{ESC}[{i}P", end="")


def backspace(i: int = 1):
    cursor_back(i)
    delete_characters(i)


def erase_characters(i: int = 1):
    print(f"{ESC}[{i}X", end="")


def insert_lines(i: int = 1):
    print(f"{ESC}[{i}L", end="")


def delete_lines(i: int = 1):
    print(f"{ESC}[{i}M", end="")


def set_tab_stop():
    print(f"{ESC}H", end="")


def tab_forward(i: int = 1):
    print(f"{ESC}[{i}I", end="")


def tab_backward(i: int = 1):
    print(f"{ESC}[{i}Z", end="")


def clear_tab_stop():
    print(f"{ESC}[0g", end="")


def clear_all_tab_stops():
    print(f"{ESC}[3g", end="")


def set_scroll_region(top: int | None = None, bottom: int | None = None):
    print(f"{ESC}[{top or ''};{bottom or ''}r", end="")


def change_title(title: str):
    print(f"{ESC}]0;{title}{ST}", end="")


def use_alternate_screen_buffer():
    print(f"{ESC}[?1049h", end="")


def use_main_screen_buffer():
    print(f"{ESC}[?1049l", end="")


def soft_reset():
    print(f"{ESC}[!p", end="")


class EraseException(Exception):
    pass


def _erase_mode(from_cursor: bool, to_cursor: bool):
    if from_cursor:
        if to_cursor:
            # entire line/display
            return 2
        else:
            return 0
    else:
        if to_cursor:
            return 1
        else:
            raise EraseException(
                "At least one of from_cursor and to_cursor must be True")


def erase_display(from_cursor: bool = True, to_cursor: bool = True):
    print(f"{ESC}[{_erase_mode(from_cursor, to_cursor)}J", end="")


def erase_line(from_cursor: bool = True, to_cursor: bool = True):
    print(f"{ESC}[{_erase_mode(from_cursor, to_cursor)}K", end="")


class Color(Enum):
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37

    BRIGHT_BLACK = 90
    BRIGHT_RED = 91
    BRIGHT_GREEN = 92
    BRIGHT_YELLOW = 93
    BRIGHT_BLUE = 94
    BRIGHT_MAGENTA = 95
    BRIGHT_CYAN = 96
    BRIGHT_WHITE = 97

    DEFAULT = 39


FORMAT_RESET = f"{ESC}[0m"


def format(s: str,
           # general options
           bold: bool = False,  # alias for fg_bright
           italic: bool = False,
           underline: bool = False,
           negative: bool = False,
           hide: bool = False,
           strikethrough: bool = False,
           double_underline: bool = False,
           overline: bool = False,
           reset: bool = True,
           # foreground
           fg_color: Color | tuple[int, int, int] | None = None,
           fg_bright: bool = False,
           fg_dim: bool = False,
           # background
           bg_color: Color | tuple[int, int, int] | None = None,
           bg_bright: bool = False,
           ):
    """ Using a custom color will cause bright options to be ignored (but not fg_dim).

    Specifying negative=True swaps the foreground and background colors. The only case where provides functionality otherwise not achievable (except by using custom colors) is dimming the background color.

    Specifying reset=False will cause the formatting to persist on all output until different formatting is specified, or it is reset using print(FORMAT_RESET, end=""). """
    """
    for i in range(0, 128):
        print(f"{ESC}[{i}m{i:03}{ESC}[m")

    reveals a few more options than presented on the Microsoft documentation, these are marked with an asterisk.

    0 reset all
    1 bold/bright — seems to affect foreground only
    *2 dim — also seems to affect foreground only, note that combining bright and dim actually does not cancel out, resulting in something between dim and default
    *3 italic
    4 underline
    7 negative — redundant with simply swapping fg/bg options, except that this makes 1 and 2 apply to the background instead
    *8 obfuscate — text does not display, but e.g. it can still be copied
    *9 strikethrough
    *21 double underline
    30-37 fg color
    38 fg custom color, 1 has seems to have no effect if this is used
    39 fg default color
    40-49 likewise for bg
    *53 overline
    90-97 bold/bright fg, redundant with 1
    100-107 bold/bright bg """

    format_options = []

    if italic:
        format_options.append(3)
    if underline:
        format_options.append(4)
    if negative:
        format_options.append(7)
    if hide:
        format_options.append(8)
    if strikethrough:
        format_options.append(9)
    if double_underline:
        format_options.append(21)
    if overline:
        format_options.append(53)

    if isinstance(fg_color, Color):
        format_options.append(str(fg_color.value))
    elif isinstance(fg_color, tuple):
        if len(fg_color) != 3:
            raise Exception("fg_color must be an RGB 3-tuple")
        format_options.extend((38, 2))
        format_options.extend(fg_color)
    if bold or fg_bright:
        format_options.append(1)
    if fg_dim:
        format_options.append(2)

    if isinstance(bg_color, Color):
        format_options.append(40 + bg_color.value +
                              (60 if bg_bright else 0))
    elif isinstance(bg_color, tuple):
        if len(bg_color) != 3:
            raise Exception("bg_color must be an RGB 3-tuple")
        format_options.extend((48, 2))
        format_options.extend(bg_color)

    if not format_options:
        # no formatting
        return s

    format_specifier = f"{ESC}[" + \
        ";".join((str(f) for f in format_options)) + "m"

    return format_specifier + s + (FORMAT_RESET if reset else "")
