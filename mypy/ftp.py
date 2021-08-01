import typing
import os
import subprocess
import multiprocessing


def win_scp(commands: typing.Iterable[str]):
    subprocess.run(
        f"\"{os.environ['PROGRAMFILES(x86)']}\\WinSCP\\WinSCP.com\" /ini=nul", shell=True, text=True, input="\n".join(commands))
