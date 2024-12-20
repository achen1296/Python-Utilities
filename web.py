import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Literal, overload
from urllib.parse import ParseResult, urlparse, urlunparse

import requests
import requests.cookies
from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        ElementNotInteractableException,
                                        NoSuchElementException,
                                        NoSuchWindowException,
                                        StaleElementReferenceException,
                                        TimeoutException)
from selenium.types import WaitExcTypes
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

import console
import files
import lists


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


def firefox_driver(profile: str | None = None, **kwargs) -> webdriver.Firefox:
    # discard log output
    service = FirefoxService(log_path="NUL:")
    if profile:
        options = FirefoxOptions()
        options.profile = FirefoxProfile(profile)
    else:
        options = None
    driver = webdriver.Firefox(options=options, service=service, **kwargs)
    driver.implicitly_wait(2)
    driver.set_page_load_timeout(15)
    return driver


def tor_driver(**kwargs) -> webdriver.Firefox:
    # discard log output
    service = FirefoxService(log_path="NUL:")
    userprofile = os.environ["userprofile"]
    tor = userprofile + r'\Programs\Tor Browser\TorBrowser'
    torexe = os.popen(
        tor+r'\Tor\tor.exe')
    profile = FirefoxProfile(
        tor+r'\Data\Browser\profile.default')
    profile.set_preference('network.proxy.type', 1)
    profile.set_preference('network.proxy.socks', '127.0.0.1')
    profile.set_preference('network.proxy.socks_port', 9050)
    profile.set_preference("network.proxy.socks_remote_dns", False)

    driver = webdriver.Firefox(
        firefox_profile=profile, service=service, **kwargs)
    driver.get("http://check.torproject.org")
    return driver


def chrome_driver(profile: files.PathLike, *, executable_path: files.PathLike | None = None, user_data_dir: files.PathLike = os.environ['LOCALAPPDATA']+"\\Google\\Chrome\\User Data") -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    options.add_argument(
        f"user-data-dir={user_data_dir}")
    options.add_argument(f"profile-directory={profile}")
    # disable (almost all) logs
    options.add_argument("--log-level=3")
    if executable_path:
        driver = webdriver.Chrome(
            executable_path=executable_path, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    driver.set_page_load_timeout(15)
    return driver


@overload
def wait_element(driver: WebDriver, css_selector: str, *, all: Literal[False] = False, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                 (ElementNotInteractableException,
                  NoSuchElementException, StaleElementReferenceException)) -> WebElement | None:
    pass


@overload
def wait_element(driver: WebDriver, css_selector: str, *, all: Literal[True] = True, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                 (ElementNotInteractableException,
                  NoSuchElementException, StaleElementReferenceException)) -> Iterable[WebElement] | None:
    pass


def wait_element(driver: WebDriver, css_selector: str, *, all: bool = False, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                 (ElementNotInteractableException,
                  NoSuchElementException, StaleElementReferenceException)
                 ) -> WebElement | Iterable[WebElement] | None:
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s). """
    last_exc = None

    def try_find(driver: WebDriver):
        nonlocal last_exc
        try:
            if all:
                return driver.find_elements(By.CSS_SELECTOR, css_selector)
            if index == 0:
                return driver.find_element(By.CSS_SELECTOR, css_selector)
            return driver.find_elements(By.CSS_SELECTOR, css_selector)[index]
        except Exception as exc:
            last_exc = exc

    try:
        return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(try_find)
    except TimeoutException:
        raise last_exc


def wait_url(driver: WebDriver, url_contains: str, timeout: int = 10):
    # only raises TimeoutException
    WebDriverWait(driver, timeout).until(
        expected_conditions.url_contains(url=url_contains))


def find_and_get_attribute(driver: WebDriver, css_selector: str, attribute: str, *, all: bool = False, timeout: int = 10, index: int = 0, ignored_exceptions: WaitExcTypes =
                           (ElementNotInteractableException,
                            NoSuchElementException, StaleElementReferenceException)
                           ) -> str | Iterable[str | None] | None:
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s) and get attribute(s). If all=True then will return a list of the results for all elements found, or specify an index > 0 to select only that index out of the list of all matching elements. """
    last_exc = None

    def try_get_attribute(driver: WebDriver):
        nonlocal last_exc
        try:
            if all:
                es = driver.find_elements(By.CSS_SELECTOR, css_selector)
                return [e.get_attribute(attribute) for e in es]
            if index == 0:
                e = driver.find_element(By.CSS_SELECTOR, css_selector)
                return e.get_attribute(attribute)
            es = driver.find_elements(By.CSS_SELECTOR, css_selector)
            return es[index].get_attribute(attribute)
        except Exception as exc:
            last_exc = exc
    try:
        return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(try_get_attribute)
    except TimeoutException:
        raise last_exc


def find_and_click(driver: WebDriver, css_selector: str, *, timeout: int = 10,  index: int = 0, ignored_exceptions: WaitExcTypes = (ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException, StaleElementReferenceException)):
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s) and click. """
    last_exc = None

    def try_click(driver: WebDriver):
        nonlocal last_exc
        try:
            if index == 0:
                e = driver.find_element(By.CSS_SELECTOR, css_selector)
                e.click()
                return True
            es = driver.find_elements(By.CSS_SELECTOR, css_selector)
            es[index].click()
            return True
        except Exception as exc:
            last_exc = exc
    try:
        WebDriverWait(driver, timeout,
                      ignored_exceptions=ignored_exceptions).until(try_click)
    except TimeoutException:
        raise last_exc


def find_and_send_keys(driver: WebDriver, css_selector: str, *keys, timeout: int = 10, index: int = 0,  ignored_exceptions: WaitExcTypes = (ElementNotInteractableException, NoSuchElementException, StaleElementReferenceException)):
    """ Replaces the TimeoutException with the last Exception raised by trying to find element(s) and send keys. """
    last_exc = None

    def try_send_keys(driver: WebDriver):
        nonlocal last_exc
        try:
            if index == 0:
                e = driver.find_element(By.CSS_SELECTOR, css_selector)
                e.send_keys(*keys)
                return True
            es = driver.find_elements(By.CSS_SELECTOR, css_selector)
            es[index].send_keys(*keys)
            return True
        except Exception as exc:
            last_exc = exc
    try:
        WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(
            try_send_keys)
    except TimeoutException:
        raise last_exc


def scroll_all_elements(driver: WebDriver, css_selector: str, *, interactable_selector: str = None, last_selector: str = None, wait=1) -> list[WebElement]:
    """Scrolls until no more new elements found by css_selector load or until last_selector is found and returns those elements"""
    last_len = 0
    if interactable_selector != None:
        interactable_element = driver.find_element(
            By.CSS_SELECTOR, interactable_selector)
    while True:
        elements = driver.find_elements(By.CSS_SELECTOR, css_selector)

        # try to find last_selector
        if last_selector != None:
            try:
                driver.find_element(By.CSS_SELECTOR, last_selector)
            except NoSuchElementException:
                pass
            else:
                break

        # see if more loaded
        len_elements = len(elements)
        if last_len < len_elements:
            last_len = len_elements
            if interactable_selector == None:
                elements[0].send_keys(Keys.END)
            else:
                interactable_element.send_keys(Keys.END)
            time.sleep(wait)
        else:
            break

    return elements


class PageReader:
    """Reads a webpage to search for links to download or open."""

    def __init__(self, get_kwargs=None):
        if get_kwargs is None:
            get_kwargs = {}
        self.get_kwargs: dict[str, str | dict[str, str]] = get_kwargs

    def can_read(self, driver: WebDriver) -> bool:
        """Whether or not the current page is readable by this PageReader."""
        return True

    def to_download(self, driver: WebDriver) -> dict[str, files.PathLike]:
        """Returns a dictionary with URLs from the current page to download as keys and the destination filenames as values. The default implementation returns all img element src attributes."""
        images: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, "img")
        download_dict = {}
        for i in images:
            if i is not None:
                src = i.get_attribute("src")
                # use default
                download_dict[src] = None
        return download_dict

    def to_open(self, driver: WebDriver) -> list[str]:
        """Returns a list of URLs from the current page to open next. The default implementation returns all a element href attributes."""
        links: list[WebElement] = driver.find_elements(By.CSS_SELECTOR, "a")
        urls = [l.get_attribute("href") for l in links]
        return [u for u in urls if u is not None]


class PageBrowser(console.Cmd):
    """Uses a set of PageReaders for browsing under human control."""

    def __init__(self, driver: WebDriver, readers: Iterable[PageReader], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = driver
        self.readers = set(readers)
        self.user_agent = self.driver.execute_script(
            "return navigator.userAgent")
        self.get = self.driver.get

        # --Cmd functions with no argument transformations required--
        self.do_o = self.open
        self.do_s = self.save_pages
        self.do_l = self.load_pages

    def new_tab(self, url: str):
        """ Open a new tab and switch to it """
        self.driver.execute_script("window.open('')")
        # switch to last, i.e. newest, window
        self.driver.switch_to.window(
            self.driver.window_handles[-1])
        self.driver.get(url)

    def close_tab(self):
        """ Close the current tab and switch to the last one """
        self.driver.close()
        # switch to new last window, somewhat mimicking normal tab close behavior
        self.driver.switch_to.window(
            self.driver.window_handles[-1])

    def open(self) -> int:
        """Open all links found on the current page by any PageReader. Returns the number of links opened."""
        count = 0
        current = self.driver.current_window_handle
        for r in self.readers:
            if r.can_read(self.driver):
                for url in r.to_open(self.driver):
                    count += 1
                    self.new_tab(url)
            self.driver.switch_to.window(current)
        return count

    def _plan_download(self) -> dict[str, tuple[files.PathLike, dict[str, str]]]:
        """ Analyze the current page using PageReaders and return an accumulated dictionary of planned downloads. """
        plan = {}
        for r in self.readers:
            if r.can_read(self.driver):
                d = r.to_download(self.driver)
                get_kwargs = r.get_kwargs
                if "headers" not in get_kwargs:
                    get_kwargs["headers"] = {}
                get_kwargs["headers"]["User-Agent"] = self.user_agent
                plan.update({
                    url: (filename, get_kwargs)
                    for url, filename in d.items()
                })
        return plan

    def download_current_page(self, wait=0, output=True) -> int:
        """Download everything on the current page found by any PageReader (using the keyword arguments to requests.get it specifies; the user agent string is also always included). Returns the number of downloads."""
        plan = self._plan_download()
        download_urls(plan, wait=wait, output=output)
        return len(plan)

    def open_and_download(self, wait=0, output=True) -> int:
        """Open each link found on the current page, analyzes, and closes the tab before moving on to the next one, then downloads everything. Returns the number of downloads. get_kwargs passed to requests.get."""
        download_count = 0
        current = self.driver.current_window_handle
        plan = {}
        for r in self.readers:
            if r.can_read(self.driver):
                to_open = r.to_open(self.driver)
                for url in to_open:
                    self.new_tab(url)
                    plan.update(self._plan_download())
                    self.close_tab()
            self.driver.switch_to.window(current)
        download_urls(plan, wait=wait, output=output)
        return download_count

    def iter_tabs(self):
        for handle in self.driver.window_handles:
            self.driver.switch_to.window(handle)
            yield handle

    def download_all(self, close_tabs: bool = True, wait=0, output=True) -> int:
        """Download everything on all open tabs found by any PageReader. Optionally closes each page after analyzing it if anything was downloaded. Returns the number of downloads. get_kwargs passed to requests.get"""
        try:
            current = self.driver.current_window_handle
        except NoSuchWindowException:
            # window being controlled was closed
            current = None
        plan = {}
        for _ in self.iter_tabs():
            page_plan = self._plan_download()
            if len(page_plan) > 0 and close_tabs and len(self.driver.window_handles) > 1:
                self.driver.close()
            plan.update(page_plan)

        if current in self.driver.window_handles:
            # return to the original active tab
            self.driver.switch_to.window(current)
        else:
            # switch to the first tab
            self.switch_tab(0)

        download_urls(plan, wait=wait, output=output)
        return len(plan)

    def switch_tab(self, tab_index: int):
        """ Specify tab index starting from 0. """
        self.driver.switch_to.window(self.driver.window_handles[tab_index])

    def save_pages(self, file: files.PathLike):
        """Save the current pages to a file"""
        urls = []
        for _ in self.iter_tabs():
            urls.append(self.driver.current_url)
        lists.write_file_list(file, urls)

    def load_pages(self, file: files.PathLike):
        """Load pages from file"""
        urls = lists.read_file_list(file)
        for u in urls:
            self.new_tab(u)

    # -- Cmd functions with argument transformations required --
    def do_d(self, wait: int = 0):
        # assume output True if used as command line
        self.download_current_page(int(wait))

    do_d.__doc__ = download_current_page.__doc__

    def do_a(self, close_tabs: bool = True, wait: int = 0):
        # assume output True if used as command line
        if isinstance(close_tabs, str):
            close_tabs = close_tabs.lower() not in {"f", "false"}
        self.download_all(close_tabs, int(wait))

    do_a.__doc__ = download_all.__doc__

    def do_t(self, tab_index: int):
        self.switch_tab(int(tab_index))
    do_t.__doc__ = switch_tab.__doc__

    def do_od(self, wait: int = 0):
        self.open_and_download(int(wait))
    do_od.__doc__ = open_and_download.__doc__


def get_firefox_cookies(profile: files.PathLike):
    con = sqlite3.connect(Path(profile)/"cookies.sqlite")
    jar = requests.cookies.RequestsCookieJar()
    for name, value, host, path in con.execute("select name, value, host, path from moz_cookies").fetchall():
        jar.set(name, value, domain=host, path=path)
    return jar


if __name__ == "__main__":
    import console
    console.traceback_wrap(PageBrowser(
        firefox_driver(), [PageReader()]).cmdloop)
