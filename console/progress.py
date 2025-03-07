import math
import time

from .ansi_escape import *


class Spinner:
    """ For printing a spinner to show that the console is working.

    Should only be used for expensive tasks, otherwise the Spinner itself will take up a lot of time relative to the actual task! """

    def __init__(self, *, min_update_time: float = 0.2, min_update_count=100, spinner_sequence="-\\|/"):
        self.last_update_time = None
        self.min_update_time = min_update_time

        self.updates = 0
        self.min_update_count = min_update_count

        self.spinner_sequence = spinner_sequence
        self.sequence_index = 0
        self.sequence_length = len(self.spinner_sequence)

    def spin(self):
        self.updates += 1
        if self.updates < self.min_update_count:
            return
        self.updates = 0
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


class Progress:
    """ Controls a progress indicator in the console that can show a fraction (e.g. "5/100"), a percentage (e.g. "5%"), or both (e.g. "5/100 5%"), optionally with explanation text. """

    def __init__(self,
                 max: int | float,
                 *,

                 show_fraction: bool = True,
                 numerator_format: str | None = None,
                 denominator_format: str | None = None,

                 show_percent: bool = True,
                 percent_format: str | None = None,

                 min_update_time: float = 0.1,
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

    def progress_text(self, value: int | float, comment: str | None):
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

    def update_progress(self, value: int | float, comment: str | None = None):
        """ Set and print the updated progress value. Comments are appended after the progress text (with a space in between). If the comment is not specified, any prior comments are not cleared (specify "") to clear comments. """
        self.last_progress = value

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

    def increase_progress(self, value: int | float, comment: str | None = None):
        self.update_progress(self.last_progress + value, comment)

    def clear(self):
        """ Clear the progress display (usually when finished). """
        # assumes cursor just reset at end of update_progress
        erase_display(from_cursor=True, to_cursor=False)


class ProgressBar(Progress):
    """ Display a visual bar along with Progress text. """

    def __init__(self, max: int | float, *, left: str = "|", right: str = "|", incomplete: str = " ", complete: str = "\u2588", width: int | None = None, **progress_kwargs):
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

    def progress_text(self, value: int | float, comment: str | None = None):
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
