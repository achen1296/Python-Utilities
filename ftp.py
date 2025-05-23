# (c) Andrew Chen (https://github.com/achen1296)

import ftplib
import os
import re
from pathlib import Path
from typing import Iterable

import files


def _str_path(path: files.PathLike) -> str:
    return str(path).replace("\\", "/")


class FTP(ftplib.FTP):
    """Adds get and put methods to ftplib FTP using its storbinary and retrbinary methods and makes get and delete recursive."""

    def __init__(self, host: str, port: int | str, user: str, pwd: str, **kwargs):
        super().__init__(**kwargs)
        self.connect(host, int(port))
        self.login(user, pwd)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.quit()

    def put(self, local: files.PathLike, remote: files.PathLike | None = None, *, exclude: Iterable[str] = []):
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
                with open(local, "rb") as f:
                    self.storbinary(f"STOR {remote}", f)
                return
            except PermissionError:
                pass
            self.mkd(remote)
            for f in Path(local).iterdir():
                recursive_put(local + "/" + f.name, remote + "/" + f.name)

        recursive_put(local, remote)

    def get(self, remote: files.PathLike, local: files.PathLike | None = None, *, exclude: Iterable[str] = []):
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
                # assume failure is due to the remote path being a folder, if not will error again on nlst
                pass
            os.remove(local)
            os.mkdir(local)
            for f in self.nlst(remote):
                recursive_get(remote + "/" + f, local + "/" + f)

        recursive_get(remote, local)

    def delete(self, file: files.PathLike):
        """Tries deleting as a file, then as a directory, then recursively."""
        file: str = _str_path(file)

        d = super().delete

        def recursive_delete(file: str):
            try:
                return d(file)
            except (ftplib.error_perm, ftplib.error_reply):
                pass
            try:
                return self.rmd(file)
            except (ftplib.error_perm, ftplib.error_reply):
                pass
            for f in self.nlst(file):
                self.delete(file + "/" + f)
            return self.rmd(file)

        recursive_delete(file)
