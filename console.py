import inspect
import platform
import re
import time
import traceback
from enum import Enum
from typing import Any, Callable, Iterable, Union


class Dots:
    """ For printing dots to show that the console is working. Every time dot() is called, a counter increments and the time since the last dot was printed is evaluated. If there were both enough calls and enough time to exceed both the minimum count and the minimum time (in seconds), a dot is printed. """

    def __init__(self, min_count: int = 100, min_time: float = 1.0, output_str="."):
        self._count = 0
        self._last_time = time.monotonic()
        self._min_count = min_count
        self._min_time = min_time
        self._output_str = output_str

    def dot(self):
        self._count += 1
        if self._count >= self._min_count and time.monotonic() - self._last_time >= self._min_time:
            self.reset()
            print(self._output_str, end="", flush=True)

    def reset(self):
        self._count = 0
        self._last_time = time.monotonic()


DOTS = Dots()


def dot():
    """ Calls dot on shared Dots object DOTS """
    DOTS.dot()


def input_generator(prompt: str = ">> "):
    while True:
        try:
            yield input(prompt)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")


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
    """ Pause execution for a certain amount of time, specified in h:mm:ss, m:ss, or s format. """
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


def repl(actions: dict[str, Union[Callable, str]], *, input_source: Iterable[str] = None, arg_transform: dict[str, Callable] = {}):
    """ actions is a dictionary with names that the console user can use to call a function. If the dictionary value is a string instead, it is treated as an alias.

    input_source is by default console user input. Mainly for testing, it may be set to e.g. a list of strings instead.

    arg_transforms should have a subset of the names in actions and contain functions to transform console input values from strings to other types.

    Special actions help/?, sleep/wait, and exit/quit are added on top of the provided actions, overriding any existing with those names. Since the arguments are usually strings, but some existing functions may expect other types, arg_transforms may be specified. """
    if input_source is None:
        input_source = input_generator()

    extra_transforms = set(arg_transform) - set(actions)
    if len(extra_transforms) > 0:
        raise Exception(
            f"Extra transformations specified for unknown actions {', '.join(extra_transforms)}")

    builtins = ["help", "?", "sleep", "wait", "exit"]

    # add special actions
    def help(*action_names: str):
        """ Show this help menu. Specify one or more commands to only show their descriptions. Specify "builtins" to see the rest of the built-in commands. """
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
                print(f"Unknown action {name}")
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
        """ Exit. """
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
                print(f"Unknown action {action_name}")

    try:
        for i in input_source:
            exited = False
            traceback_wrap(lambda: call_action(i), pause_message=None)
            if exited:
                break
    except EOFError:
        return


def bell():
    """ Print the "bell" character. Works cross-platform because it is part of ASCII. """
    print('\u0007', end="")


def pause(message: str = "Press Enter to continue...: "):
    """ Mimics the Windows pause console command (but works on any platform because it just uses the builtin input), including the same message by default. """
    input(message)


def traceback_wrap(f: Callable, pause_message: str = "Press Enter to continue...", pause_on_exc_only=True) -> Any:
    """ Wraps a function in an exception handler that prints tracebacks. Intended as a wrapper for standalone script main methods -- pauses to keep the console popup window open so the output may be inspected. Set pause_message=None to skip pausing, usually if this is used inside something else. """
    try:
        return f()
    except (Exception, KeyboardInterrupt) as x:
        if isinstance(x, KeyboardInterrupt):
            print("KeyboardInterrupt")
        else:
            traceback.print_exc()
        bell()
        if pause_on_exc_only and pause_message is not None:
            pause(pause_message)
    finally:
        if not pause_on_exc_only and pause_message is not None:
            pause(pause_message)


if platform.system() == "Windows":
    # learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences
    # all of these functions print directly to the console because they are not supposed to be used anywhere else anyway

    ESC = "\x1b"
    ST = ESC + "\\"

    def change_title(title: str):
        """ Uses Windows console virtual terminal sequences, must be on Windows. """
        print(f"{ESC}]0;{title}{ST}", end="")

    def cursor_back(i: int):
        """ Uses Windows console virtual terminal sequences, must be on Windows. """
        print(f"{ESC}[{i}D", end="")

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

    def print_formatted(*values,
                        # general options
                        italic: bool = False,
                        underline: bool = False,
                        negative: bool = False,
                        obfuscate: bool = False,
                        strikethrough: bool = False,
                        double_underline: bool = False,
                        overline: bool = False,
                        # foreground
                        fg_color: Union[Color, tuple[int, int, int]] = None,
                        fg_bright: bool = False,
                        fg_dim: bool = False,
                        # background
                        bg_color: Union[Color, tuple[int, int, int]] = None,
                        bg_bright: bool = False,
                        # print params
                        **kwargs
                        ):
        """ Using a custom color will cause bright options to be ignored (but not fg_dim).

        Specifying negative=True swaps the foreground and background colors. The only case where provides functionality otherwise not achievable (except by using custom colors) is dimming the background color. 

        Uses Windows console virtual terminal sequences, must be on Windows. """
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
        if obfuscate:
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

        format_specifier = f"{ESC}[" + \
            ";".join((str(f) for f in format_options)) + "m"
        format_reset = f"{ESC}[0m"

        sep = kwargs["sep"]
        del kwargs["sep"]

        print(format_specifier + sep.join((str(v)
              for v in values)) + format_reset, **kwargs)

    class Spinner:
        """ For printing a spinner to show that the console is working. Every time spin() is called, a counter increments and the time since the last visual update is evaluated. If there were both enough calls and enough time the spinner updates.

        Uses Windows console virtual terminal sequences, must be on Windows. """

        def __init__(self, min_count: int = 100, min_time: float = 0.2, spinner_sequence="-/|\\"):
            if platform.system() != "Windows":
                raise NotImplementedError
            self._count = 0
            self._last_time = time.monotonic()
            self._min_count = min_count
            self._min_time = min_time
            self._spinner_sequence = spinner_sequence
            self._sequence_index = 0
            self._sequence_length = len(self._spinner_sequence)

        def spin(self):
            self._count += 1
            if self._count >= self._min_count and time.monotonic() - self._last_time >= self._min_time:
                self.reset()
                cursor_back(1)
                print(
                    self._spinner_sequence[self._sequence_index], end="", flush=True)
                self._sequence_index = (
                    self._sequence_index+1) % self._sequence_length

        def reset(self):
            self._count = 0
            self._last_time = time.monotonic()

    SPINNER = Spinner()

    def spin():
        """ Calls spin on shared Spinner object SPINNER """
        SPINNER.spin()

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

    repl({
        "test": test_action
    }, arg_transform={
        "test": test_transform
    })
