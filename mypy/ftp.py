import os
from ftplib import FTP
import ftplib
import typing


class SimpleFTP(FTP):
    """Adds get and put methods to ftplib FTP using its storbinary and retrbinary methods."""

    def put(self, local: os.PathLike, remote: os.PathLike = None):
        if remote is None:
            remote = local
        self.storbinary(f"STOR {remote}", open(local, "rb"))

    def get(self, remote: os.PathLike, local: os.PathLike = None):
        if local is None:
            local = remote
        with open(local, "wb") as f:
            self.retrbinary(f"RETR {remote}", f.write)

    def simple_delete(self, file: os.PathLike):
        """Tries deleting as a file, then as a directory, then recursively."""
        file = str(file)
        try:
            self.delete(file)
            return
        except (ftplib.error_perm, ftplib.error_reply):
            pass
        try:
            self.rmd(file)
            return
        except (ftplib.error_perm, ftplib.error_reply):
            pass
        for f in self.nlst(file):
            self.simple_delete(file + "/" + f)
        self.rmd(file)


def ftp(host: str, port: typing.Union[int, str], user: str, pwd: str):
    f = SimpleFTP()
    f.connect(host, int(port))
    f.login(user, pwd)
    return f
