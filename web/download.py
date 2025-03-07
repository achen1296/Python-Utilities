# (c) Andrew Chen (https://github.com/achen1296)

import time
from pathlib import Path
from urllib.parse import ParseResult, urlparse, urlunparse

import requests
import requests.cookies

import console
import files


def url_filename(url: str):
    """ Get filename in a URL pointing to a file -- the last path component. """
    return files.remove_forbidden_chars(Path(urlparse(url).path).name, name_only=True)


class DownloadException(Exception):
    pass


def download_url(url: str, dst: files.PathLike | None = None, *, output=True, chunk_size=8192, **get_kwargs):
    """ If file = None, the name is inferred from the last piece of the URL path. get_kwargs passed to requests.get. Returns destination file Path. """
    url_parsed = urlparse(url)
    # remove query, parameters, and fragment, since these are unnecessary (and can even alter the downloaded file, such as by reducing the image resolution)
    url_parsed = ParseResult(scheme=url_parsed.scheme, netloc=url_parsed.netloc,
                             path=url_parsed.path, params='', query='', fragment='')
    url = urlunparse(url_parsed)
    if dst is None:
        dst = url_filename(url)
    else:
        dst = files.remove_forbidden_chars(str(dst))
    dst = Path(dst).absolute()

    with requests.get(url, stream=True, **get_kwargs) as req:
        if not req.ok:
            raise DownloadException(url, req.status_code,
                                    req.reason, get_kwargs)
        if output:
            content_length = int(req.headers.get("content-length", "0"))
            if content_length == 0:
                # not specified in the response
                prog = console.Spinner()
                download_info_str = f"Downloading <{url}> -> <{dst}>"
                print(download_info_str)

                def increase_progress(*_):
                    prog.spin()

                def clear():
                    console.cursor_up(
                        console.measure_lines(download_info_str))
                    console.cursor_horizontal_absolute(1)
                    console.erase_display(from_cursor=True, to_cursor=False)
            else:
                prog = console.ProgressBar(content_length)
                increase_progress = prog.increase_progress
                clear = prog.clear
                prog.update_progress(0, f"Downloading <{url}> -> <{dst}>")
        with open(dst, "wb") as f:
            for chunk in req.iter_content(chunk_size):
                if output:
                    increase_progress(len(chunk))
                f.write(chunk)
        if output:
            clear()

    return dst


def download_urls(plan: dict[str, tuple[files.PathLike, dict[str, str]]], *, wait=0, output=True):
    """ plan should be a dictionary mapping a URL to a tuple containing the download destination and a dictionary of keyword arguments for requests.get. If the destination is given as None, it will be in the current working directory with a name determined from the end of the URL path.

    Optionally waits for the specified number of seconds in between downloads to avoid pressuring the server; by default does not wait. """
    if output:
        counter = 0
        total = len(plan)
        num_width = len(str(total))
    for url in plan:
        dst, get_kwargs = plan[url]
        if wait > 0:
            time.sleep(wait)
        if output:
            counter += 1
            print(f"{counter: >{num_width}}/{total}")
        download_url(url, dst, output=output, **get_kwargs)
        if output:
            # to rewrite the download count
            console.cursor_up(1)
    if output:
        # to remove the download count
        console.erase_line()
