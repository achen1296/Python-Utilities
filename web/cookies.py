import sqlite3
from pathlib import Path

import requests
import requests.cookies

import files


def get_firefox_cookies(profile: files.PathLike):
    con = sqlite3.connect(Path(profile)/"cookies.sqlite")
    jar = requests.cookies.RequestsCookieJar()
    for name, value, host, path in con.execute("select name, value, host, path from moz_cookies").fetchall():
        jar.set(name, value, domain=host, path=path)
    return jar
