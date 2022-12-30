import re
import traceback
import typing
import strings
import time
import inspect


class Dots:
    """ For printing dots to show that the console is working. Every time dot() is called, a counter increments and the time since the last dot was printed is evaluated. If there were both enough calls and enough time to exceed both the minimum count and the minimum time (in seconds), a dot is printed. """

    def __init__(self, min_count: int, min_time: float, output_callback=None, output_str="."):
        self._count = 0
        self._last_time = time.monotonic()
        self._min_count = min_count
        self._min_time = min_time
        if output_callback is None:
            self._output_callback = lambda s: print(s, end="", flush=True)
        else:
            self._output_callback = output_callback
        self._output_str = output_str

    def dot(self):
        self._count += 1
        if self._count >= self._min_count and time.monotonic() - self._last_time >= self._min_time:
            self.reset()
            self._output_callback(self._output_str)

    def reset(self):
        self._count = 0
        self._last_time = time.monotonic()


DOTS = Dots(100, 1.0)


def dot():
    """ Calls dot on shared Dots(100, 1.0) object DOTS """
    DOTS.dot()


def input_generator(prompt: str = ">> "):
    while True:
        try:
            yield input(prompt)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")


def cmd_split(s: str) -> typing.Iterable[list[str]]:
    """Splits commands by semicolons, splits arguments by whitespace, but neither when inside a string delimited with ' or ". String arguments can include ' or " using backslash escape."""

    def unescape(s: str) -> str:
        return s.replace('\\"', '"').replace("\\'", "'")

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


def repl(actions: dict[str, typing.Callable], *, input_source: typing.Iterable[str] = None, arg_transform: dict[str, typing.Callable] = {}):
    """ Special actions help/?, sleep/wait, and exit/quit are added on top of the provided actions, overriding any existing with those names. Since the arguments are usually strings, but some existing functions may expect other types, arg_transforms may be specified. """
    if input_source is None:
        input_source = input_generator()

    extra_transforms = set(arg_transform) - set(actions)
    if len(extra_transforms) > 0:
        raise Exception(
            f"Extra transformations specified for unknown actions {', '.join(extra_transforms)}")

    # add special actions
    def help(*action_names: str):
        """ Show this help menu. Specify one or more commands to only show their descriptions. """
        if len(action_names) == 0:
            # get all actions if none are specified
            items = [(name, action)
                     for name, action in actions.items()]
        else:
            items = [(name, actions.get(name))
                     for name in action_names]
        for name, a in items:
            if a is None:
                print(f"Unknown action {name}")
                continue
            if name in arg_transform:
                sig = f"{inspect.signature(arg_transform[name])} -> "
            else:
                sig = ""
            sig += str(inspect.signature(a))
            print(f"{name}: {sig} {a.__doc__ or ''}")

    actions["help"] = actions["?"] = help

    actions["sleep"] = actions["wait"] = sleep

    def exit():
        """ Exit. """
        nonlocal exited
        exited = True

    actions["exit"] = exit

    def call_action(i: str):
        for args in cmd_split(i):
            if len(args) == 0:
                continue
            action_name = args[0]
            args = args[1:]
            if action_name in actions:
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
    print('\u0007', end="")  # "bell" ASCII character


def pause(message: str = "Press Enter to continue...: "):
    """ Mimics the Windows pause console command, including the same message by default. """
    input(message)


def traceback_wrap(f: typing.Callable, pause_message: str = "Press Enter to continue...") -> typing.Any:
    """ Wraps a function in an exception handler that prints tracebacks. Intended as a wrapper for standalone script main methods -- pauses to keep the console popup window open so the output may be inspected. Set pause_message=None to skip pausing, usually if this is used inside something else. """
    result = None
    try:
        result = f()
    except Exception:
        traceback.print_exc()
        bell()
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        if pause_message is not None:
            pause(pause_message)
        return result


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
