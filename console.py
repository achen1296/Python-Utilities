import traceback
import typing
import strings


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
        try:
            actions[args[0]](*args[1:])
        except KeyError:
            print(f"Unknown action {args[0]}")
            traceback.print_exc()
        except TypeError:
            print(f"Invalid arguments {args[1:]}")
            traceback.print_exc()
        except Exception:
            traceback.print_exc()
