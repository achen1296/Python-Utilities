import os
from ftplib import FTP as _FTP
import ftplib
import re
import typing


class FTP(_FTP):
    """Adds get and put methods to ftplib FTP using its storbinary and retrbinary methods and makes get and delete recursive."""

    def __init__(self, host: str, port: typing.Union[int, str], user: str, pwd: str):
        ftplib.FTP.__init__(self)
        self.connect(host, int(port))
        self.login(user, pwd)

    def put(self, local: os.PathLike, remote: os.PathLike = None):
        if remote is None:
            remote = local
        self.storbinary(f"STOR {remote}", open(local, "rb"))

    def get(self, remote: os.PathLike, local: os.PathLike = None, *, exclude: typing.Iterable[str] = []):
        remote = str(remote).replace("\\", "/")
        if local is None:
            local = remote
        else:
            local = str(local).replace("\\", "/")

        def recursive_get(remote: os.PathLike, local: os.PathLike = None):
            for e in exclude:
                if re.search(e, remote):
                    return
            try:
                with open(local, "wb") as f:
                    self.retrbinary(f"RETR {remote}", f.write)
                return
            except (ftplib.error_perm, ftplib.error_reply):
                os.remove(local)
                os.mkdir(local)
            for f in self.nlst(remote):
                recursive_get(remote + "/" + f, local + "/" + f)

        recursive_get(remote, local)

    def delete(self, file: os.PathLike):
        """Tries deleting as a file, then as a directory, then recursively."""
        file = str(file)
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
