import inspect
import math
import re
import time
import traceback
from enum import Enum
from shutil import get_terminal_size
from typing import Any, Callable, Iterable, Union


def print_as_exc(s: str, **print_kwargs):
    print(format(s, fg_color=Color.RED), **print_kwargs)
    bell()


def input_generator(prompt: str = ">> "):
    while True:
        try:
            yield input(prompt)
        except KeyboardInterrupt:
            print_as_exc("KeyboardInterrupt")


def cmd_split(s: str) -> Iterable[list[str]]:
    """Splits commands by semicolons, splits arguments by whitespace, but neither when inside a string delimited with ' or ". String arguments can include ' or " using backslash escape."""

    start = -1
    end = -1
    quote = None
    args = []

    s_len = len(s)
    for i in range(0, s_len):
        if i == 0:
            last = None
        else:
            last = s[i-1]
        c = s[i]
        if (c in ['"', "'"] and last != "\\"):
            if quote is None:
                # found the beginning of a string
                quote = c
                start = i

                semicolon_split = s[end+1:start].split(";")
                semi_len = len(semicolon_split)
                if semi_len > 1:
                    yield args + semicolon_split[0].split()
                    for cmd in semicolon_split[1:-1]:
                        yield cmd.split()
                    args = []
                if semi_len >= 1:
                    args += semicolon_split[-1].split()

            elif quote == c:
                # found the end of a string
                quote = None
                end = i
                args.append(s[start+1:end])

    if quote is not None:
        raise Exception("Unbalanced quotes")

    semicolon_split = s[end+1:].split(";")
    semi_len = len(semicolon_split)
    if semi_len > 1:
        yield args + semicolon_split[0].split()
        for cmd in semicolon_split[1:-1]:
            yield cmd.split()
        args = []
    if semi_len >= 1:
        args += semicolon_split[-1].split()
    yield args


def sleep(time_str: str):
    """Pause execution for a certain amount of time, specified in h:mm:ss, m:ss, or s format. """
    match: re.Match = re.match("^(\d+):(\d{2}):(\d{2})$", time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
    else:
        match: re.Match = re.match("^(\d):(\d{2})$", time_str)
        if match:
            hours = 0
            minutes = int(match.group(1))
            seconds = int(match.group(2))
        else:
            match: re.Match = re.match("^(\d+)$", time_str)
            if match:
                hours = minutes = 0
                seconds = int(match.group(1))
            else:
                raise Exception("Invalid time string")
    if not (0 <= seconds <= 59 and 0 <= minutes <= 59):
        raise Exception("Invalid time string")
    sleep_time = seconds + 60*(minutes + 60*hours)
    print(f"Sleeping for {sleep_time} seconds")
    time.sleep(sleep_time)


def repl(actions: dict[str, Union[Callable, str]] = None, *, input_source: Iterable[str] = None, arg_transform: dict[str, Callable] = None, default: Union[Callable, str] = None):
    """actions is a dictionary with names that the console user can use to call a function. If the dictionary value is a string instead, it is treated as an alias.

    input_source is by default console user input. Mainly for testing, it may be set to e.g. a list of strings instead.

    arg_transforms should have a subset of the names in actions and contain functions to transform console input values from strings to other types.

    If an unknown command is given and default is specified, then all of the arguments *including the first one that was attempted as a command name* are given to it. If specified as a string, then that is used as an alias for an action to call.

    Special actions help/?, sleep/wait, and exit/quit are added on top of the provided actions, overriding any existing with those names. Since the arguments are usually strings, but some existing functions may expect other types, arg_transforms may be specified. """
    if actions is None:
        actions = {}

    if input_source is None:
        input_source = input_generator()

    if arg_transform is None:
        arg_transform = {}

    extra_transforms = set(arg_transform) - set(actions)
    if len(extra_transforms) > 0:
        raise Exception(
            f"Extra transformations specified for unknown actions {', '.join(extra_transforms)}")

    builtins = ["help", "?", "sleep", "wait", "exit"]

    # add special actions
    def help(*action_names: str):
        """Show this help menu. Specify one or more commands to only show their descriptions. Specify "builtins" to see the rest of the built-in commands. """
        action_names: set[str] = set(action_names)
        if len(action_names) == 0:
            # get all actions if none are specified, but the builtins will be excluded except help
            items = [(name, action)
                     for name, action in actions.items() if name not in builtins or name == "help"]
        else:
            if "builtins" in action_names:
                action_names.remove("builtins")
                action_names.update(builtins)
            items = [(name, actions.get(name))
                     for name in action_names]
        # sort by name
        items.sort(key=lambda tup: tup[0])
        for name, a in items:
            if a is None:
                print_as_exc(f"Unknown action {name}")
                continue
            if isinstance(a, str):
                print(f"{name}: Alias for \"{a}\"")
                continue
            if name in arg_transform:
                sig = f"{inspect.signature(arg_transform[name])} -> "
            else:
                sig = ""
            sig += str(inspect.signature(a))
            doc = (a.__doc__ or "").replace("\n", "\n\t")
            print(f"{name}: {sig}\n\t{doc}")

    actions["help"] = help
    actions["?"] = "help"

    actions["sleep"] = sleep
    actions["wait"] = "sleep"

    def exit():
        """Exit. """
        nonlocal exited
        exited = True

    actions["exit"] = exit

    def call_action(i: str):
        command_num = 0
        for args in cmd_split(i):
            if len(args) == 0:
                continue
            command_num += 1
            if command_num > 1:
                print(">> " + (" ".join(args)))
            action_name = args[0]
            if action_name not in actions and isinstance(default, str):
                action_name = default
            else:
                args = args[1:]
            if action_name in actions:
                while isinstance(actions[action_name], str):
                    # follow alias chain
                    action_name = actions[action_name]
                if action_name in arg_transform:
                    args = arg_transform[action_name](
                        *args)
                result = actions[action_name](*args)
                if result is not None:
                    print(result)
            else:
                if isinstance(default, Callable):
                    default(action_name, *args)
                else:
                    print_as_exc(f"Unknown action {action_name}")

    try:
        for i in input_source:
            exited = False
            traceback_wrap(lambda: call_action(i), pause_message=None)
            if exited:
                break
    except EOFError:
        return


def bell():
    """Print the "bell" character. """
    print('\u0007', end="")


def pause(message: str = "Press Enter to continue...: "):
    """Mimics the Windows pause console command (but works on any platform because it just uses the builtin input), including the same message by default. """
    input(message)


def traceback_wrap(f: Callable, pause_message: str = "Press Enter to continue...", pause_on_exc_only=True) -> Any:
    """Wraps a function in an exception handler that prints tracebacks. Intended as a wrapper for standalone script main methods -- pauses to keep the console popup window open so the output may be inspected. Set pause_message=None to skip pausing, usually if this is used inside something else. """
    try:
        return f()
    except (Exception, KeyboardInterrupt) as x:
        if isinstance(x, KeyboardInterrupt):
            err_text = "KeyboardInterrupt\n"
        else:
            err_text = traceback.format_exc()
        # traceback.format_exc includes a \n
        print_as_exc(err_text, end="")
        if pause_on_exc_only and pause_message is not None:
            pause(pause_message)
    finally:
        if not pause_on_exc_only and pause_message is not None:
            pause(pause_message)


# en.wikipedia.org/wiki/ANSI_escape_code
# learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences
# all of these functions print directly to the console because they are not supposed to be used anywhere else anyway

ESC = "\x1b"
ST = ESC + "\\"


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


def set_scroll_region(top: int = None, bottom: int = None):
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
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7
    DEFAULT = 9


FORMAT_RESET = f"{ESC}[0m"


def format(s: str,
           # general options
           italic: bool = False,
           underline: bool = False,
           negative: bool = False,
           hide: bool = False,
           strikethrough: bool = False,
           double_underline: bool = False,
           overline: bool = False,
           reset: bool = True,
           # foreground
           fg_color: Union[Color, tuple[int, int, int]] = None,
           fg_bright: bool = False,
           fg_dim: bool = False,
           # background
           bg_color: Union[Color, tuple[int, int, int]] = None,
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
        format_options.append(str(30 + fg_color.value))
    elif isinstance(fg_color, tuple):
        if len(fg_color) != 3:
            raise Exception("fg_color must be an RGB 3-tuple")
        format_options.extend((38, 2))
        format_options.extend(fg_color)
    if fg_bright:
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


class Spinner:
    """ For printing a spinner to show that the console is working. 

    Should only be used for expensive tasks, otherwise the Spinner itself will take up a lot of time relative to the actual task! """

    def __init__(self, min_update_time: float = 0.2, spinner_sequence="-\\|/"):
        self.last_update_time = None
        self.min_update_time = min_update_time
        self.spinner_sequence = spinner_sequence
        self.sequence_index = 0
        self.sequence_length = len(self.spinner_sequence)

    def spin(self):
        now = time.monotonic()
        if self.last_update_time is not None and now < self.last_update_time + self.min_update_time:
            return
        self.last_update_time = now
        cursor_back(1)
        print(
            self.spinner_sequence[self.sequence_index], end="", flush=True)
        self.sequence_index = (
            self.sequence_index+1) % self.sequence_length


SPINNER = Spinner()


def spin():
    """ Calls spin on shared Spinner object SPINNER. """
    SPINNER.spin()


class Progress:
    """ Controls a progress indicator in the console that can show a fraction (e.g. "5/100"), a percentage (e.g. "5%"), or both (e.g. "5/100 5%"), optionally with explanation text. """

    def __init__(self,
                 max: Union[int, float],
                 *,

                 show_fraction: bool = True,
                 numerator_format: str = None,
                 denominator_format: str = None,

                 show_percent: bool = True,
                 percent_format: str = None,

                 min_update_time: float = 0,
                 ):
        """ Leaving the format arguments as None will automatically:
        - For fraction numerator/denominator:
            - Format integers with no decimal points
            - Format floats with 2 digits after the decimal point
                - The type of the numerator should be the same as the denominator
            - Give the numerator the same amount of space as is taken by the denominator, padding with spaces
        - For the percentage:
            - Use 2 decimal digits for the percentage
            - Make it 7 characters wide (the length of "100.00%")
        - Align right

        Under the assumption that all progress values are between 0 and max inclusive, this should keep the text width consistent. Otherwise, it is up to the user to keep the width consistent.

        Nothing else should be printed from the moment of construction until it is no longer needed (presumably finishing with a clear() call). Use the comment parameter to add additional text below. 
        """
        self.max = max
        self.show_fraction = show_fraction
        self.show_percent = show_percent

        self.denominator_format = denominator_format or (
            "d" if isinstance(max, int) else ".2f")
        self.denominator = f"{max:{self.denominator_format}}"
        self.number_width = len(self.denominator)

        self.numerator_format = numerator_format or (
            f" >{self.number_width}d" if isinstance(max, int) else f" >{self.number_width}.2f")

        self.percent_format = percent_format or " >7.2%"

        self.min_update_time = min_update_time
        self.last_update_time = None

    def progress_text(self, value: Union[int, float], comment: str):
        prog_text = ""
        if self.show_fraction:
            prog_text += f"{value:{self.numerator_format}}/{self.denominator}"
            if self.show_percent:
                prog_text += " "

        if self.show_percent:
            prog_text += f"{value/self.max:{self.percent_format}}"

        if comment:  # not None or ""
            prog_text += " "
        return prog_text

    def update_progress(self, value: Union[int, float], comment: str = None):
        """ Set and print the updated progress value. Comments are appended after the progress text (with a space in between). If the comment is not specified, any prior comments are not cleared (specify "") to clear comments. """
        now = time.monotonic()
        if self.last_update_time is not None and now < self.last_update_time + self.min_update_time:
            return
        self.last_update_time = now

        prog_text = self.progress_text(value, comment)
        print(prog_text, end="")

        if comment is not None:
            erase_display(from_cursor=True, to_cursor=False)
            print(comment, end="")
            cursor_up(comment.count("\n"))

        # in case of subclass override
        cursor_up(prog_text.count("\n"))
        cursor_horizontal_absolute(1)

    def clear(self):
        """ Clear the progress display (usually when finished). """
        # assumes cursor just reset at end of update_progress
        erase_display(from_cursor=True, to_cursor=False)


class ProgressBar(Progress):
    """ Display a visual bar along with Progress text. """

    def __init__(self, max: Union[int, float], *, left: str = "|", right: str = "|", incomplete: str = " ", complete: str = "\u2588", width: Union[int, None] = None, **progress_kwargs):
        """ left and right: bar boundary characters
        incomplete: the initial character the bar is filled with
        complete: the character the bar is replaced with as progress increases
        width: the width that ALL of the characters, including the progress text and the bar, may take up; leave as None to adapt to the current terminal width on each update (via get_terminal_size) """
        super().__init__(max=max, **progress_kwargs)
        self.left = left
        self.right = right
        self.incomplete = incomplete
        self.complete = complete
        self.width = width

    def progress_text(self, value: Union[int, float], comment: str = None):
        """ Append the progress bar onto the normal progress text and push comments onto the next line. """
        prog_text = super().progress_text(value, comment)
        if not prog_text.endswith(" "):
            prog_text += " "

        total_width = self.width or get_terminal_size().columns
        bar_width = total_width - \
            (len(prog_text) + len(self.left) + len(self.right))

        complete_chars = math.floor((value/self.max) * bar_width + 0.5)
        incomplete_chars = bar_width - complete_chars
        bar = self.left + (self.complete * complete_chars) + \
            (self.incomplete * incomplete_chars) + self.right

        # push the comment onto the next line
        if comment and not comment.startswith("\n"):
            bar += "\n"

        return prog_text + bar


if __name__ == "__main__":
    result = list(cmd_split("a;b;c d"))
    assert result == [["a"], ["b"], ["c", "d"]], result

    result = list(cmd_split("'a';\"b;\\\"c\" d"))
    assert result == [["a"], ["b;\\\"c", "d"]], result

    def test_action(x: int):
        "Add 1 to x"
        return x+1

    def test_transform(x: str):
        return int(x)

    def test_exc():
        raise Exception

    def progress_test():
        # ints
        prog = ProgressBar(100)
        for i in range(0, 101):
            prog.update_progress(i, f"{i:03}"*((100-i)//30+1) + "\n\ncomment")
            time.sleep(0.05)
        prog.clear()

        # floats
        prog = ProgressBar(100.)
        for i in range(0, 101):
            prog.update_progress(
                float(i), f"{i:03}"*((100-i)//30+1) + "\n\ncomment")
            time.sleep(0.05)
        prog.clear()

        # comment persistence, rate limit
        prog = ProgressBar(100, min_update_time=.5)
        prog.update_progress(0, "persistent comment")
        for i in range(1, 101):
            prog.update_progress(i)
            time.sleep(0.05)
        prog.clear()

        # test rate limit
        for _ in range(0, 100):
            spin()
            time.sleep(0.05)
        backspace()

    repl({
        "test": test_action,
        "e": test_exc,
        "p": progress_test
    }, arg_transform={
        "test": test_transform,
    })
