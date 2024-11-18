from pathlib import Path

import files


class FileBackedData:
    """ Subclasses should mostly only need to override read() and write(). """

    def __init__(self, file: files.PathLike, read_args: tuple = (), read_kwargs: dict = {}, write_args: tuple = (), write_kwargs: dict = {}):
        """ Use as a context manager or explicitly call flush or close(). Either way, will use the write_args and write_kwargs when calling write(). """
        self.file = Path(file)

        self.read(*read_args, **read_kwargs)

        self.write_args = write_args
        self.write_kwargs = write_kwargs

    def write(self, *args, **kwargs):
        pass

    def read(self, *args, **kwargs):
        pass

    def close(self):
        # currently just flushes, but might do something different in the future...
        self.flush()

    def flush(self):
        self.write(*self.write_args, **self.write_kwargs)

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
