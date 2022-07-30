import os
import ftplib
import ftplib
from pathlib import Path
import re
import typing


def _str_path(path: os.PathLike) -> str:
    return str(path).replace("\\", "/")


class FTP(ftplib.FTP):
    """Adds get and put methods to ftplib FTP using its storbinary and retrbinary methods and makes get and delete recursive."""

    def __init__(self, host: str, port: typing.Union[int, str], user: str, pwd: str):
        ftplib.FTP.__init__(self)
        self.connect(host, int(port))
        self.login(user, pwd)

    def put(self, local: os.PathLike, remote: os.PathLike = None, *, exclude: typing.Iterable[str] = []):
        local = _str_path(local)
        if remote is None:
            remote = local
        else:
            remote = _str_path(remote)

        def recursive_put(local: str, remote: str):
            for e in exclude:
                if re.search(e, local):
                    return
            try:
                self.storbinary(f"STOR {remote}", open(local, "rb"))
                return
            except PermissionError:
                pass
            self.mkd(remote)
            for f in Path(local).iterdir():
                recursive_put(local + "/" + f.name, remote + "/" + f.name)

        recursive_put(local, remote)

    def get(self, remote: os.PathLike, local: os.PathLike = None, *, exclude: typing.Iterable[str] = []):
        remote = _str_path(remote)
        if local is None:
            local = remote
        else:
            local = _str_path(local)

        def recursive_get(remote: str, local: str):
            for e in exclude:
                if re.search(e, remote):
                    return
            try:
                with open(local, "wb") as f:
                    self.retrbinary(f"RETR {remote}", f.write)
                return
            except (ftplib.error_perm, ftplib.error_reply):
                pass
            os.remove(local)
            os.mkdir(local)
            for f in self.nlst(remote):
                recursive_get(remote + "/" + f, local + "/" + f)

        recursive_get(remote, local)

    def delete(self, file: os.PathLike):
        """Tries deleting as a file, then as a directory, then recursively."""
        file = _str_path(file)

        def recursive_delete(file: str):
            try:
                super().delete(file)
                return
            except (ftplib.error_perm, ftplib.error_reply):
                pass
            try:
                self.rmd(file)
                return
            except (ftplib.error_perm, ftplib.error_reply):
                pass
            for f in self.nlst(file):
                self.delete(file + "/" + f)
            self.rmd(file)

        recursive_delete(file)
