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
            break


def repl(actions: dict[str, typing.Callable], *, input_source: typing.Iterable[str] = None):
    if input_source is None:
        input_source = input_generator()

    for i in input_source:
        args = strings.argument_split(i)
        if args[0] == "help":
            for name, a in actions.items():
                print(f"{name}: {inspect.signature(a)} {a.__doc__}")
            continue
        try:
            if args[0] in actions:
                print(actions[args[0]](*args[1:]))
            else:
                print(f"Unknown action {args[0]}")
        except Exception:
            traceback.print_exc()
