import cmd
import inspect
import math
import os
import re
import time
import traceback
from enum import Enum
from pathlib import Path
from shutil import get_terminal_size
from typing import Any, Callable, Iterable, Union

import strings


def print_as_exc(s: str, **print_kwargs):
    print(format(s, fg_color=Color.RED), **print_kwargs)
    bell()


def input_generator(prompt: str = ">> "):
    while True:
        try:
            yield input(prompt)
        except KeyboardInterrupt:
            print_as_exc("KeyboardInterrupt")


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


class Cmd(cmd.Cmd):
    """ Adds some more features onto cmd.Cmd:
    - pre-includes these actions:
        - help/? (as in the superclass)
        - exit/quit
        - wait/sleep
    - enter multiple commands at once separated by semicolons, but not ones in quoted strings
    - arguments are split by whitespace, but not whitespace in quoted strings, and these arguments are sent to functions separately using * unpacking
        - the first split item is the command prefix, overriding the default behavior using identifier characters, and this item is not sent to the function
            - it is still sent to the default function, similar to the superclass sending the entire command string
        - commands may have aliases
            - ? is an alias of help (as in the superclass)
            - quit is an alias of exit
            - wait is an alias of sleep
            - added a help section for aliases
        - for compatibility with the superclass, if this does not work, the arguments are re-joined using spaces and that is sent to the method as one argument
    - Python Exceptions and keyboard interrupts are caught and printed
    - help shows function signatures
    - help adapts its output to the current terminal size
    - catch KeyboardInterrupts instead of completely terminating, but terminate on EOF
    """
    # override
    prompt = ">> "
    # new attributes
    aliases_header = "Aliases:"
    scripts_header = "Scripts: "
    command_sep = "\s*;\s*"
    comment = "\s*#"

    def __init__(self, aliases: dict[str, str] = None, scripts_dir: os.PathLike = None, script_suffix=".script", *args, **kwargs):
        """ If scripts_dir is not specified, command execution will not attempt to find scripts. """
        super().__init__(*args, **kwargs)
        if aliases is None:
            aliases = {}
        self.aliases = aliases
        self.aliases.update({
            "?": "help",
            "quit": "exit",
            "wait": "sleep",
        })
        if scripts_dir is None:
            self.scripts_dir = None
        else:
            self.scripts_dir = Path(scripts_dir)
        self.script_suffix = script_suffix

    def do_exit(self):
        """ Exit the console. """
        # stop flag
        return True

    def do_sleep(self, time_str: str):
        sleep(time_str)

    do_sleep.__doc__ = sleep.__doc__

    def cmdloop(self, intro=None):
        """ Modifies the superclass cmdloop to catch KeyboardInterrupt without stopping, but conversely will stop on EOF (like the Python interactive shell). """

        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey+": complete")
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro)+"\n")

            def loop_body():
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                    if isinstance(line, list):
                        whitespace = '\s+'
                        joined_line = ' '.join(
                            (s if not re.search(whitespace, s) else f'"{s}"' for s in line))
                        print(f">> {joined_line}")
                    else:
                        print(f">> {line}")
                else:
                    if self.use_rawinput:
                        try:
                            line = input(self.prompt)
                        except EOFError:
                            # stop on EOF
                            return True
                    else:
                        self.stdout.write(self.prompt)
                        self.stdout.flush()
                        line = self.stdin.readline()
                        if not len(line):
                            # stop on EOF
                            return True
                        else:
                            line = line.rstrip('\r\n')
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
                return stop

            stop = False
            while not stop:
                try:
                    stop = traceback_wrap(
                        loop_body, pause_message=None, reraise=True)
                except:
                    self.cmdqueue.clear()

            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass

    def precmd(self, line: Union[str, list]):
        """ Split commands by self.command_sep. """
        if isinstance(line, list):
            # pass through pre-parsed command
            return line
        # keep empty splits since this can be used intentionally to repeat a command
        cmds = strings.argument_split(
            line, self.command_sep, split_compounds=False, remove_empty_args=False)
        if len(cmds) <= 1:
            return line
        # add new commands onto the FRONT of the queue so that things will execute in the expected order in case nested
        self.cmdqueue = cmds[1:] + self.cmdqueue
        return cmds[0]

    def onecmd(self, line: Union[str, list[str]]):
        """ Interpret the argument as though it had been typed in response
        to the prompt.

        Overridden and modified from the superclass to split arguments into lists of strings by whitespace and catch and print Python Exceptions and keyboard interrupts. Also accepts pre-split arguments (such as from script enqueueing) analogous to subprocess.run.
        """
        if isinstance(line, str):
            line = line.strip()
            if not line:
                return self.emptyline()
            cmd, *args = strings.argument_split(line)
        elif isinstance(line, list):
            cmd, *args = line
        else:
            raise TypeError(
                "Input must be a string or a pre-parsed list of strings")
        while cmd in self.aliases:
            cmd = self.aliases[cmd]
        try:
            func = getattr(self, 'do_' + cmd)
        except AttributeError:
            if self.scripts_dir is not None and (script_path := self._script_path(cmd)).exists():
                func = self.execute_script
                # pass the script path to execute_script
                args = [script_path] + args
            else:
                func = self.default
                # pass the first split argument to default
                args = [cmd] + args
        self.lastcmd = line
        # try:
        return func(*args)
        # except TypeError:
        # for compatibility with superclass
        # return func(" ".join(args))

    def _script_path(self, script_name):
        return self.scripts_dir.joinpath(script_name).with_suffix(self.script_suffix)

    def do_help(self, *cmds: str):
        """ List available commands with "help" or detailed help with "help cmd".

        If the class was instantiated with a scripts_dir, can find script files as well, and if there is a comment (a line *starting* with a #, though command arguments may contain #'s) on the first non-empty line, will print that as a docstring. """
        if cmds:
            for cmd in cmds:
                try:
                    help_func = getattr(self, 'help_' + cmd)
                except AttributeError:
                    if cmd in self.aliases:
                        print(
                            f"Alias for {self.aliases[cmd]}", file=self.stdout)
                        continue
                    else:
                        try:
                            cmd_func = getattr(self, 'do_' + cmd)
                            print(inspect.signature(cmd_func),
                                  file=self.stdout)
                            doc: str = cmd_func.__doc__
                            if doc:
                                print()

                                # strip leading whitespace based on the second non-whitespace line
                                lines = doc.split("\n")
                                found_first_non_white = False
                                l2 = None
                                for l in lines:
                                    if l.strip():
                                        # not all whitespace
                                        if not found_first_non_white:
                                            found_first_non_white = True
                                        else:
                                            # found the second non-whitespace line
                                            l2 = l
                                            break
                                if l2:
                                    match = re.match("\s*", l2)
                                    whitespace_prefix = match.string[:match.end(
                                    )]
                                    lines = [l.removeprefix(
                                        whitespace_prefix)for l in lines]
                                    doc = "\n".join(lines)

                                print(doc, file=self.stdout)
                                continue
                        except AttributeError:
                            pass

                        script_path = self._script_path(cmd)
                        if script_path.exists():
                            found_script_doc_comment = False
                            with open(script_path) as f:
                                for line in f:
                                    line = line.strip()
                                    if not line:
                                        continue
                                    if match := re.match(self.comment, line):
                                        print(line[match.end():],
                                              file=self.stdout)
                                        found_script_doc_comment = True
                                    else:
                                        # found a non-comment first
                                        break
                        if found_script_doc_comment:
                            continue

                        print(str(self.nohelp % (cmd,)), file=self.stdout)
                        continue
                help_func()
        else:
            names = sorted(set(dir(self)))
            cmds = {name[3:] for name in names if name[:3] == 'do_'}
            help = {name[5:] for name in names if name[:5] == 'help_'}

            cmds_doc = {cmd for cmd in cmds if getattr(
                self, "do_" + cmd).__doc__} | (help & cmds)
            misc_topics = help - cmds
            cmds_undoc = cmds - cmds_doc
            scripts = [f.stem for f in self.scripts_dir.iterdir()
                       if f.suffix == self.script_suffix] if self.scripts_dir else []
            print(self.doc_leader, file=self.stdout)
            terminal_width = get_terminal_size().columns
            # the cmdlen argument is strangely not used in the superclass, so I have replaced it with None
            self.print_topics(self.doc_header, list(
                cmds_doc), None, terminal_width)
            self.print_topics(self.misc_header, list(misc_topics),
                              None, terminal_width)
            self.print_topics(self.undoc_header, list(cmds_undoc),
                              None, terminal_width)
            self.print_topics(self.aliases_header,
                              list(self.aliases), None, terminal_width)
            self.print_topics(self.scripts_header,
                              list(scripts), None, terminal_width)

    def execute_script(self, script: os.PathLike, *script_args):
        """ Used before the default method if the class was instantiated with a scripts_dir.

        Searches for text files in the scripts_dir with a name matching the first argument and the right suffix. The remaining arguments are used to replace $0, $1, etc. in each command in the script *only* if they appear as the entire argument. If not enough arguments are given, the extras are completely dropped. Can also use $x-y etc. for all arguments in the inclusive range x to y (omit either to capture all arguments before/after a certain point), so e.g. $- or $0- captures all of the arguments. The arguments will not actually be packaged back into a single input string, so they will not be split up again, meaning it is safe to have arguments with spaces.

        For example, using the default arguments, if the current directory contains a file named "example.script" which contains:

        ``sleep $0``

        ``help $1 $2``

        then entering

        ``example 5 quit``

        into the console will sleep for 5 seconds, then print out the help text for ``quit`` ($3 gets dropped).

        If a range argument capture is used, it will expand into as many arguments as were captured! If it is specified inside an argument along with exact text, that exact text will also be multiplied. This can happen multiple times as well. For example, if "example.script" contains:

        ``echo $-$-``

        (where the echo action reproduces its arguments) and you call ``example 1 2 3``, the output will be
        ``11 12 13 21 22 23 31 32 33``

        On the other hand, note that if the arguments in the specified range are not given at all, then the arguments will simply disappear.
        """

        cmds = []

        len_script_args = len(script_args)

        with open(script) as f:
            for line in f:
                line = line.strip()
                if not line:
                    # empty line
                    continue
                if re.match(self.comment, line):
                    # comment
                    continue
                for cmd in strings.argument_split(line, self.command_sep, split_compounds=False):
                    cmd_args = strings.argument_split(cmd)
                    i = 0
                    while i < len(cmd_args):
                        ca = cmd_args[i]
                        while group := re.search("(\$(\d+)?-(\d+)?)|\$(\d+)", ca):
                            if group.group(1):
                                # range
                                if group.group(2):
                                    start = int(group.group(2))
                                else:
                                    start = 0
                                if group.group(3):
                                    end = int(group.group(3))
                                else:
                                    end = len_script_args
                            else:
                                # assert match.group(4)
                                start = int(group.group(4))
                                end = start+1
                            cmd_args[i:i+1] = [ca[:group.start()] + sa + ca[group.end():] for sa in
                                               script_args[start:end]]
                            if i >= len(cmd_args):
                                # last arg was deleted
                                break
                            ca = cmd_args[i]
                        i += 1
                    cmds.append(cmd_args)

        # add new commands onto the FRONT of the queue so that things will execute in the expected order in case nested
        self.cmdqueue = cmds + self.cmdqueue

        # enqueued commands will begin being executed automatically


def bell():
    """Print the "bell" character. """
    print('\u0007', end="")


def pause(message: str = "Press Enter to continue...: "):
    """Mimics the Windows pause console command (but works on any platform because it just uses the builtin input), including the same message by default. """
    input(message)


def traceback_wrap(f: Callable, pause_message: str = "Press Enter to continue...", pause_on_exc_only: bool = True, reraise: bool = False) -> Any:
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
        if reraise:
            raise
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

    @staticmethod
    def clear():
        backspace()


SPINNER = Spinner()


def spin():
    """ Calls spin on shared Spinner object SPINNER. """
    SPINNER.spin()


ARC_SPINNER_SEQUENCE = "\u25dc\u25dd\u25de\u25df"


def measure_lines(text: str, terminal_width: int = None):
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
        self.last_progress = 0

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
        self.last_progress = value

        cursor_save()
        now = time.monotonic()
        if self.last_update_time is not None and now < self.last_update_time + self.min_update_time:
            return
        self.last_update_time = now

        prog_text = self.progress_text(value, comment)
        print(prog_text, end="", flush=True)

        if comment is not None:
            erase_display(from_cursor=True, to_cursor=False)
            print(comment, end="", flush=True)
        cursor_up(measure_lines(prog_text + (comment or ""))-1)
        cursor_horizontal_absolute(1)

    def increase_progress(self, value: Union[int, float], comment: str = None):
        self.update_progress(self.last_progress + value, comment)

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


def test():
    class CmdTest(Cmd):
        def __init__(self):
            super().__init__(scripts_dir=".")
            self.do_help2 = self.do_help

        def do_a(self, x: int):
            "Add 1 to x"
            print(int(x)+1)

        def do_e(self, _):
            raise Exception

        def do_p(self, _):
            # ints
            prog = ProgressBar(100)
            for i in range(0,  101):
                prog.update_progress(
                    i, f"{i:03}"*((100-i)//30+1) + "\n\ncomment")
                time.sleep(0.05)
            prog.clear()

            # floats, long comments
            prog = ProgressBar(100.)
            for i in range(0, 101):
                prog.update_progress(
                    float(i), "long comment "*15)
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

        def do_echo(self, *args):
            print(args)

        def do_write(self):
            with open("example.script", "w") as f:
                f.write("# example script doc comment\n")
                f.write("echo $0 $1 $2\n")
                f.write("echo $0- a\n")
                f.write("echo $-$-\n")
                f.write("echo $-$1-$2-\n")

    CmdTest().cmdloop()


if __name__ == "__main__":
    test()
