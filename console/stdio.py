# (c) Andrew Chen (https://github.com/achen1296)


from abc import ABCMeta
import asyncio
from queue import Empty, Queue
from subprocess import PIPE
import sys
from threading import Thread
from typing import Any


class StdinReaderThread(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_queue: Queue[str] = Queue()

    def run(self):
        while True:
            self.input_queue.put(sys.stdin.readline())


class StdioMiddleman(metaclass=ABCMeta):
    process: asyncio.subprocess.Process

    @classmethod
    async def create(cls, *subprocess_args, **subprocess_kwargs):
        self = cls()
        self.process = await asyncio.create_subprocess_exec(*subprocess_args, **subprocess_kwargs, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        return self

    def __init__(self):
        # use a daemon thread so at end of program doesn't block on stdin.readline() until user presses enter
        self.stdin_reader_thread = StdinReaderThread(daemon=True)
        self.stdin_reader_thread.start()

    def on_stdin(self, stdin: str) -> Any:
        """ React to input on stdin of the *wrapper* process (line-buffered). Return a falsy value (including implicit None) to forward the data to stdin of the *wrapped* process, return truthy to prevent this. """
        pass

    def on_stdout(self, stdout: str) -> Any:
        """ React to output on stdout from the *wrapped* process (block-buffered). Return a falsy value (including implicit None) to forward the data to stdout of the *wrapper* process, return truthy to prevent this. """
        pass

    def on_stderr(self, stderr: str) -> Any:
        """ React to output on stderr from the *wrapped* process (block-buffered). Return a falsy value (including implicit None) to forward the data to stderr of the *wrapper* process, return truthy to prevent this. """
        pass

    def send_input(self, input: str):
        """ Send input to stdin of the *wrapped* process. """
        assert self.process.stdin
        self.process.stdin.write(input.encode("utf8"))

    async def run(self):
        async def forward_input(process: asyncio.subprocess.Process):
            # https://stackoverflow.com/questions/31510190/aysncio-cannot-read-stdin-on-windows
            assert process.stdin
            while process.returncode is None:
                try:
                    input = self.stdin_reader_thread.input_queue.get(block=False)
                except Empty:
                    continue
                finally:
                    await asyncio.sleep(0)
                if self.on_stdin(input):
                    continue  # do not forward
                self.send_input(input)

        async def forward_output(process: asyncio.subprocess.Process):
            assert process.stdout
            while process.returncode is None:
                output = await process.stdout.read(4096)
                if process.stdout.at_eof():
                    # EOF, server terminated (return code check doesn't seem to work?)
                    break
                if self.on_stdout(str(output, encoding="utf8")):
                    continue  # do not forward
                print(str(output, encoding="utf8"), end="")

        async def forward_error(process: asyncio.subprocess.Process):
            assert process.stderr
            while process.returncode is None:
                error_output = await process.stderr.read(4096)
                if process.stderr.at_eof():
                    # EOF, server terminated (return code check doesn't seem to work?)
                    break
                if self.on_stderr(str(error_output, encoding="utf8")):
                    continue  # do not forward
                print(str(error_output, encoding="utf8"), end="", file=sys.stderr)

        # process termination wait should be first completed as the others never exit their loops
        coroutines = [self.process.wait(), forward_input(self.process), forward_output(self.process),
                      forward_error(self.process)]
        await asyncio.wait([asyncio.create_task(coro) for coro in coroutines], return_when=asyncio.FIRST_COMPLETED)
