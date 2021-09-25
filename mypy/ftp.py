import typing
import os
import subprocess


def win_scp(commands: typing.Iterable[str]):
    subprocess.run(
        f"\"{os.environ['PROGRAMFILES(x86)']}\\WinSCP\\WinSCP.com\" /ini=nul", shell=True, text=True, input="\n".join(commands))


class WinSCPCommands:
    """Collector for WinSCP commands.
    Example use:
    w = WinSCPCommands().open("<site>").lcd("C:\\\\\\\\").get("file.txt").run()
    """

    def __init__(self):
        self.working_dir = os.getcwd()
        self.commands = []

    def run(self):
        win_scp(self.commands)

    def cd(self, dir: str = None):
        if dir == None:
            self.commands.append("cd")
        else:
            self.commands.append(f"cd {dir}")
        return self

    def close(self):
        self.commands.append("close")
        return self

    def __get_put_parse(self, get_or_put: str, files: typing.Union[str, typing.Iterable[str]], local_destination: str):
        """Shared logic for get and put commands for the handling of the file parameters."""
        if isinstance(files, str):
            if local_destination == None:
                # automatically downloads to local working directory
                self.commands.append(f"{get_or_put} {files}")
            else:
                self.commands.append(
                    f"{get_or_put} {files} {local_destination}")
        else:
            assert isinstance(files, typing.Iterable)
            if local_destination == None:
                # local destination parameter mandatory if more than one file specified
                local_destination = self.working_dir
            self.commands.append(
                " ".join([get_or_put] + files + [local_destination]))

    def get(self, files: typing.Union[str, typing.Iterable[str]], local_destination: str = None):
        self.__get_put_parse("get", files, local_destination)
        return self

    def lcd(self, dir: str):
        # for future calls to get or put
        self.working_dir = dir
        self.commands.append(f"lcd {dir}")
        return self

    def open(self, user: str, pwd: str, host: str, port: typing.Union[str, int]):
        self.commands.append(f"open {user}:{pwd}@{host}:{port}")
        return self

    def open_preformatted(self, preformatted: str):
        """Alternative to open for when your FTP login information is already formatted."""
        self.commands.append(f"open {preformatted}")
        return self

    def put(self, files: typing.Union[str, typing.Iterable[str]], local_destination: str = None):
        self.__get_put_parse("put", files, local_destination)
        return self

    def rm(self, files: typing.Union[str, typing.Iterable[str]]):
        if isinstance(files, str):
            self.commands.append(f"rm {files}")
        else:
            self.commands.append(" ".join(["rm"]+files))
        return self
