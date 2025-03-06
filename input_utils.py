import re


def get_int_input(prompt: str = "", err_prompt: str = "Please input a valid integer"):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print(err_prompt)


def get_int_input_in_range(range: int | tuple[int, int], prompt: str = "", err_prompt: str | None = None):
    if isinstance(range, int):
        min = 0
        max = range
    else:
        min, max = range
    if err_prompt is None:
        err_prompt = f"Please input a valid integer in the range {min}-{max}"
    while True:
        i = get_int_input(prompt, err_prompt)
        if min <= i <= max:
            return i
        else:
            print(err_prompt)


def get_y_n_input(prompt: str):
    while True:
        v = input(prompt)
        if not re.fullmatch("\\s*(y(es)?|no?)\\s*", v, re.I):
            print("Answer yes/no or just y/n")
            continue
        return bool(re.fullmatch("\\s*y(es)?\\s*", v))
