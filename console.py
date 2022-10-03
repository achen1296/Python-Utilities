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


def repl(actions: dict[str, typing.Callable], *, input_source: typing.Iterable[str] = None, arg_transform: dict[str, typing.Callable] = {}):
    if input_source is None:
        input_source = input_generator()

    for i in input_source:
        args = strings.argument_split(i)
        action_name = args[0]
        args = args[1:]
        if action_name == "help":
            for name, a in actions.items():
                if name in arg_transform:
                    sig = f"{inspect.signature(arg_transform[name])} -> "
                else:
                    sig = ""
                sig += str(inspect.signature(a))
                print(f"{name}: {sig} {a.__doc__ or ''}")
            continue
        try:
            if action_name in actions:
                if action_name in arg_transform:
                    args = arg_transform[action_name](*args)
                print(actions[action_name](args))
            else:
                print(f"Unknown action {action_name}")
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
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
