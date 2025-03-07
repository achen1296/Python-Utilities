import cmd
import inspect
import os
import re
import time
import traceback
from pathlib import Path
from shutil import get_terminal_size
from typing import Any, Callable

import files
import strings

from .ansi_escape import *
from .progress import *
from .stdio import *

IN_VS_CODE = (os.environ.get("TERM_PROGRAM") == "vscode")


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
    match: re.Match[str] | None = re.match(
        "^(\\d+):(\\d{2}):(\\d{2})$", time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
    else:
        match = re.match("^(\\d):(\\d{2})$", time_str)
        if match:
            hours = 0
            minutes = int(match.group(1))
            seconds = int(match.group(2))
        else:
            match = re.match("^(\\d+)$", time_str)
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


CmdLineType = str | list[str] | tuple[str, ...]


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
    - catch KeyboardInterrupts instead of completely terminating, but terminate on EOF after calling do_exit
    """
    # override
    prompt = ">> "
    # new attributes
    aliases_header = "Aliases:"
    scripts_header = "Scripts: "
    command_sep = "\\s*;\\s*"
    comment = "\\s*#"

    def __init__(self, aliases: dict[str, str] | None = None, scripts_dir: files.PathLike | None = None, script_suffix=".script", *args, **kwargs):
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

        # when errors occur, cmdqueue is moved into this variable for the continue command
        self.dropped_cmdqueue = []

    def do_exit(self):
        """ Exit the console. """
        # stop flag
        return True

    def do_sleep(self, time_str: str):
        sleep(time_str)

    do_sleep.__doc__ = sleep.__doc__

    def cmdloop(self, intro=None):
        """ Modifies the superclass cmdloop to catch KeyboardInterrupt without stopping, but conversely will stop on EOF (like the Python interactive shell), just after calling do_exit. """

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

            line = ""

            def loop_body():
                nonlocal line
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                    if isinstance(line, list):
                        whitespace = '\\s+'
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
                            self.do_exit()
                            return True
                    else:
                        self.stdout.write(self.prompt)
                        self.stdout.flush()
                        line = self.stdin.readline()
                        if not len(line):
                            # stop on EOF
                            self.do_exit()
                            return True
                        else:
                            line = line.rstrip('\r\n')
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
                if not self.cmdqueue:
                    stop = self.postqueue(stop, line)
                return stop

            stop = False
            while not stop:
                try:
                    stop = traceback_wrap(
                        loop_body, pause_message=None, reraise=True)
                except:
                    # put the failed command back on the front
                    self.dropped_cmdqueue = [line]+self.cmdqueue
                    self.cmdqueue = []

            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass

    def precmd(self, line: CmdLineType):  # type: ignore (intentional incompatible override)
        """ Split commands by self.command_sep. """
        if not isinstance(line, str):
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

    def onecmd(self, line: CmdLineType) -> bool | None:  # type: ignore
        # (intentional incompatible override)
        """ Interpret the argument as though it had been typed in response
        to the prompt.

        Overridden and modified from the superclass to split arguments into lists of strings by whitespace and catch and print Python Exceptions and keyboard interrupts. Also accepts pre-split arguments (such as from script enqueueing) analogous to subprocess.run.
        """
        if isinstance(line, str):
            line = line.strip()
            if not line:
                return self.emptyline()
            cmd, *args = strings.argument_split(line)
        elif isinstance(line, list) or isinstance(line, tuple):
            cmd, *args = line
        else:
            raise TypeError(
                "Input must be a string or a pre-parsed list of strings")
        while cmd in self.aliases:
            cmd = self.aliases[cmd]
        try:
            func: Callable[..., bool | None] = getattr(self, 'do_' + cmd)
        except AttributeError:
            if self.scripts_dir is not None and (script_path := self._script_path(cmd)).exists():
                func = self.execute_script
                # pass the script path to execute_script
                args = [str(script_path)] + args
            else:
                func = self.default
                # pass the first split argument to default
                args = [cmd] + args
        self.lastcmd: CmdLineType = line  # type: ignore
        # (intentional incompatible override)

        # try:
        return func(*args)
        # except TypeError:
        # for compatibility with superclass
        # return func(" ".join(args))

    def postcmd(self, stop: bool | None, line: CmdLineType):  # type: ignore
        # (intentional incompatible override)
        return stop

    def postqueue(self, stop: bool | None, line: CmdLineType):
        """ Run after all of the commands in a queue (including a single command) """
        return stop

    def do_continue(self):
        """ Continue a command queue (either script or using command separators) after an error, including retrying the command that produced the error. """
        self.cmdqueue = self.dropped_cmdqueue

    def _script_path(self, script_name):
        return self.scripts_dir.joinpath(script_name).with_suffix(self.script_suffix)

    LEVENSHTEIN_MAX = 3

    def default(self, cmd, *_: str):
        print("Unknown command. ", end="")
        first = True
        for attr in dir(self):
            if attr.startswith("do_"):
                attr_cmd = attr.removeprefix("do_")
                d = strings.levenshtein(cmd, attr_cmd)
                if d < self.LEVENSHTEIN_MAX:
                    if first:
                        print("Did you mean one of these?")
                        first = False
                    print(attr_cmd + "\t", end="")
        print()

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
                                    # this pattern is guaranteed to match
                                    match: re.Match[str] = re.match(
                                        "\\s*", l2)  # type: ignore
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
                                    match: re.Match[str] | None
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
            cmds: set[str] = {name[3:] for name in names if name[:3] == 'do_'}
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

    def execute_script(self, script: files.PathLike, *script_args):
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
                        while group := re.search("(\\$(\\d+)?-(\\d+)?)|\\$(\\d+)", ca):
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


def pause(message: str = "Press Enter to continue...: "):
    """Mimics the Windows pause console command (but works on any platform because it just uses the builtin input), including the same message by default. """
    input(message)


def traceback_wrap[T](f: Callable[[], T], pause_message: str | None = "Press Enter to continue...", pause_on_exc_only: bool = True, reraise: bool = False, no_pause_in_vs_code: bool = True) -> T | None:
    """Wraps a function in an exception handler that prints tracebacks. Intended as a wrapper for standalone script main methods -- pauses to keep the console popup window open so the output may be inspected. Set pause_message=None to skip pausing, usually if this is used inside something else. """
    exception_occurred = False
    try:
        return f()
    except (Exception, KeyboardInterrupt) as x:
        exception_occurred = True
        if isinstance(x, KeyboardInterrupt):
            err_text = "KeyboardInterrupt\n"
        else:
            err_text = traceback.format_exc()
        # traceback.format_exc includes a \n
        print_as_exc(err_text, end="")
        if reraise:
            raise
    finally:
        if (exception_occurred or not pause_on_exc_only) \
                and pause_message is not None \
                and not (no_pause_in_vs_code and IN_VS_CODE):
            pause(pause_message)


def main_wrap(module_name: str, module_file: str, main_function: Callable[[], Any]):
    """ Call as: `main_wrap(__name__, __file__, main)` """
    if module_name == "__main__":
        os.chdir(Path(module_file).parent)
        traceback_wrap(main_function)


def split_print(*args, file=None, **kwargs):
    """ Print both to the specified file and sys.stdout as usual. A convenient way to use this is to reassign print = console.split_print. """
    print(*args, **kwargs)
    print(*args, file=file, **kwargs)


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
